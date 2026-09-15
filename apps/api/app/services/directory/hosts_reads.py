"""Code hosts connected to an organization, read: the hosts, the one for a url, credentials (refreshed when they expire)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select

from action_platform.core.exception import ProviderError
from app.core.db.models import (
    SourceHost,
)
from app.core.shared.clock import now
from app.core.shared.credentials import (
    Credentials,
    CredentialsError,
)
from app.core.shared.urls import GitUrl
from app.services.directory.base import (
    REFRESH_MARGIN,
    DirectoryBase,
)
from app.services.integrations.hosts import PROVIDERS


class HostsReads(DirectoryBase):
    def hosts_of(self, organization_id: str) -> list[SourceHost]:
        return list(
            self.db.scalars(
                select(SourceHost)
                .where(SourceHost.organization_id == organization_id)
                .order_by(SourceHost.created_at)
            )
        )

    def host_id_for_url(self, organization_id: str, url: str) -> Optional[str]:
        kind = GitUrl(url).kind

        if kind is None:
            return None

        return next(
            (h.id for h in self.hosts_of(organization_id) if h.kind == kind), None
        )

    def credentials_for(
        self, organization_id: str, host_id: Optional[str]
    ) -> Optional[Credentials]:
        if not host_id or self.sealer is None:
            return None

        host = self.db.scalar(
            select(SourceHost).where(
                SourceHost.id == host_id, SourceHost.organization_id == organization_id
            )
        )

        if host is None:
            return None

        token = self.sealer.open(host.token_encrypted)

        if (
            host.auth_kind == "oauth"
            and host.refresh_token_encrypted
            and host.expires_at
            and host.expires_at - now() < REFRESH_MARGIN
        ):
            token, refreshed, expires_at = self._refresh(
                host.kind, self.sealer.open(host.refresh_token_encrypted)
            )
            host.token_encrypted = self.sealer.seal(token)

            if refreshed:
                host.refresh_token_encrypted = self.sealer.seal(refreshed)

            host.expires_at = expires_at
            self.db.flush()

        return Credentials(
            host.kind, token, host.username, host.base_url, host.default_owner
        )

    def _refresh(
        self, kind: str, refresh_token: str
    ) -> tuple[str, Optional[str], Optional[datetime]]:
        app = self.oauth_app(kind)

        if app is None:
            raise CredentialsError(
                f"the {kind} token expired and no OAuth app is configured on the API to refresh it"
            )

        try:
            return PROVIDERS.get(kind).refresh(app, refresh_token)
        except ProviderError as e:
            raise CredentialsError(str(e)) from e
