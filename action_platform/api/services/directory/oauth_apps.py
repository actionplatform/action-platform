"""The OAuth apps the platform uses to connect code hosts."""

from __future__ import annotations

from typing import Optional


from action_platform.api.db.models import OAuthApp as OAuthAppRow
from action_platform.api.services.shared.common import now
from action_platform.api.services.shared.credentials import (
    OAuthApp,
    oauth_app_for,
)
from action_platform.api.services.directory.base import (
    PROVIDERS,
    DirectoryBase,
    DirectoryError,
)


class OauthAppsReads(DirectoryBase):
    def oauth_app(self, provider: str) -> Optional[OAuthApp]:
        row = self.db.get(OAuthAppRow, provider)

        if row is not None and self.sealer is not None:
            return OAuthApp(
                row.client_id,
                self.sealer.open(row.client_secret_encrypted),
                row.base_url,
                row.slug,
            )

        return oauth_app_for(provider)

    def oauth_apps(self) -> dict[str, Optional[OAuthApp]]:
        return {provider: self.oauth_app(provider) for provider in PROVIDERS}


class OauthAppsWrites(OauthAppsReads):
    def save_oauth_app(
        self,
        provider: str,
        client_id: str,
        client_secret: str,
        base_url: Optional[str],
        slug: Optional[str] = None,
    ) -> OAuthApp:
        if provider not in PROVIDERS:
            raise DirectoryError("unknown provider")

        if self.sealer is None:
            raise DirectoryError("auth secret is not configured")

        client_id = client_id.strip()
        client_secret = client_secret.strip()

        if not client_id or not client_secret:
            raise DirectoryError("client id and secret are required")

        row = self.db.get(OAuthAppRow, provider) or OAuthAppRow(provider=provider)
        row.client_id = client_id
        row.client_secret_encrypted = self.sealer.seal(client_secret)
        row.base_url = (base_url or "").strip() or None
        row.slug = slug or row.slug
        row.updated_at = now()
        self.db.add(row)
        self.db.flush()

        return OAuthApp(client_id, client_secret, row.base_url, row.slug)

    def clear_oauth_app(self, provider: str) -> None:
        row = self.db.get(OAuthAppRow, provider)

        if row is not None:
            self.db.delete(row)
            self.db.flush()
