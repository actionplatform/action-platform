"""A live token for a connected service: the stored one, refreshed through the provider when it is about to expire."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from action_platform.core.exception import ProviderError
from action_platform.plugins.options import Credential
from app.core.auth.crypto import Sealer
from app.core.db.models import ServiceConnection
from app.core.shared.clock import now
from app.core.shared.credentials import CredentialsError
from app.repositories.base import REFRESH_MARGIN
from app.repositories.integrations import ConnectionsReads, OAuthAppsReads
from app.services.integrations.connections.registry import (
    ConnectionProviders,
    connection_providers,
)


class FreshConnections(ConnectionsReads, OAuthAppsReads):
    def __init__(
        self,
        db: DbSession,
        sealer: Optional[Sealer] = None,
        connections: Optional[ConnectionProviders] = None,
    ) -> None:
        super().__init__(db, sealer)
        self.connections = connections or connection_providers()

    def credential(self, organization_id: str, kind: str) -> Optional[Credential]:
        if self.sealer is None:
            return None

        row = self.connection(organization_id, kind)

        if row is None:
            return None

        if self._expiring(row):
            row = self._locked(row)

            if self._expiring(row):
                self._refresh_connection(row)

        return Credential(
            kind=row.kind,
            token=self.sealer.open(row.token_encrypted),
            login=row.login,
            api_url=row.base_url,
            scopes=tuple(row.scopes.split()) if row.scopes is not None else None,
        )

    def _locked(self, row: ServiceConnection) -> ServiceConnection:
        """The row again, held until the transaction ends, so two calls never spend the same refresh token."""
        return self.db.execute(
            select(ServiceConnection)
            .where(ServiceConnection.id == row.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one()

    @staticmethod
    def _expiring(row: ServiceConnection) -> bool:
        return bool(
            row.refresh_token_encrypted
            and row.expires_at
            and row.expires_at - now() < REFRESH_MARGIN
        )

    def _refresh_connection(self, row: ServiceConnection) -> None:
        app = self.oauth_app(row.kind)

        if app is None:
            raise CredentialsError(
                f"the {row.kind} token expired and no OAuth app is configured to refresh it; reconnect {row.kind}"
            )

        try:
            grant = self.connections.get(row.kind).refresh(
                app, self.sealer.open(row.refresh_token_encrypted)
            )
        except ProviderError as e:
            raise CredentialsError(
                f"{row.kind}: refreshing the connection failed ({e}); reconnect {row.kind}"
            ) from e

        row.token_encrypted = self.sealer.seal(grant.access)

        if grant.refresh:
            row.refresh_token_encrypted = self.sealer.seal(grant.refresh)

        row.expires_at = grant.expires_at

        if grant.scopes is not None:
            row.scopes = " ".join(grant.scopes)

        self.db.flush()
