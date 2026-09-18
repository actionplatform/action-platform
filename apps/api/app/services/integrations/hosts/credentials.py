"""A live token for a code host: the stored one, refreshed through the provider when it is about to expire."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from action_platform.core.exception import ProviderError
from app.core.db.models import SourceHost
from app.core.shared.clock import now
from app.core.shared.credentials import Credentials, CredentialsError
from app.repositories.base import REFRESH_MARGIN
from app.repositories.integrations import HostsReads, OAuthAppsReads
from app.services.integrations.hosts import PROVIDERS


class FreshCredentials(HostsReads, OAuthAppsReads):
    def credentials_for(
        self, organization_id: str, host_id: Optional[str]
    ) -> Optional[Credentials]:
        if not host_id or self.sealer is None:
            return None

        host = self.host(organization_id, host_id)

        if host is None:
            return None

        if self._expiring(host):
            self._refresh_host(host)

        return super().credentials_for(organization_id, host_id)

    @staticmethod
    def _expiring(host: SourceHost) -> bool:
        return bool(
            host.auth_kind == "oauth"
            and host.refresh_token_encrypted
            and host.expires_at
            and host.expires_at - now() < REFRESH_MARGIN
        )

    def _refresh_host(self, host: SourceHost) -> None:
        token, refreshed, expires_at = self._refresh(
            host.kind, self.sealer.open(host.refresh_token_encrypted)
        )
        host.token_encrypted = self.sealer.seal(token)

        if refreshed:
            host.refresh_token_encrypted = self.sealer.seal(refreshed)

        host.expires_at = expires_at
        self.db.flush()

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
