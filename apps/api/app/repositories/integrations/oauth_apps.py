"""The OAuth apps the platform uses to connect code hosts."""

from __future__ import annotations

import secrets
from typing import Optional

from app.core.db.models import OAuthApp as OAuthAppRow
from app.core.shared.clock import now
from app.core.shared.credentials import AppKey, OAuthApp
from app.repositories.base import (
    PROVIDERS,
    DirectoryBase,
    DirectoryError,
)


class OAuthAppsReads(DirectoryBase):
    def oauth_app(self, provider: str) -> Optional[OAuthApp]:
        row = self.db.get(OAuthAppRow, provider)

        if row is not None and self.sealer is not None:
            return OAuthApp(
                row.client_id,
                self.sealer.open(row.client_secret_encrypted),
                row.base_url,
                row.slug,
            )

        return OAuthApp.from_env(provider)

    def app_key(self, provider: str) -> Optional[AppKey]:
        row = self.db.get(OAuthAppRow, provider)

        if (
            row is None
            or self.sealer is None
            or not row.app_id
            or not row.private_key_encrypted
        ):
            return None

        return AppKey(row.app_id, self.sealer.open(row.private_key_encrypted), row.slug)

    def app_webhook_secret(self, provider: str) -> Optional[str]:
        row = self.db.get(OAuthAppRow, provider)

        if row is None or self.sealer is None or not row.webhook_secret_encrypted:
            return None

        return self.sealer.open(row.webhook_secret_encrypted)

    def oauth_apps(self) -> dict[str, Optional[OAuthApp]]:
        return {provider: self.oauth_app(provider) for provider in PROVIDERS}


class OAuthAppsWrites(OAuthAppsReads):
    def save_oauth_app(
        self,
        provider: str,
        client_id: str,
        client_secret: str,
        base_url: Optional[str],
        slug: Optional[str] = None,
        app_id: Optional[str] = None,
        private_key: Optional[str] = None,
        webhook_secret: Optional[str] = None,
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
        row.client_secret_encrypted = self.sealer.seal(client_secret)
        row.base_url = (base_url or "").strip() or None
        same_app = row.client_id == client_id
        row.client_id = client_id
        row.slug = slug or (row.slug if same_app else None)
        row.app_id = app_id or (row.app_id if same_app else None)
        row.private_key_encrypted = (
            self.sealer.seal(private_key)
            if private_key
            else (row.private_key_encrypted if same_app else None)
        )
        row.webhook_secret_encrypted = (
            self.sealer.seal(webhook_secret)
            if webhook_secret
            else (row.webhook_secret_encrypted if same_app else None)
        )
        row.updated_at = now()
        self.db.add(row)
        self.db.flush()

        return OAuthApp(client_id, client_secret, row.base_url, row.slug)

    def rotate_app_webhook_secret(self, provider: str) -> str:
        if self.sealer is None:
            raise DirectoryError("auth secret is not configured")

        row = self.db.get(OAuthAppRow, provider)

        if row is None:
            raise DirectoryError(f"no {provider} app is configured")

        secret = secrets.token_urlsafe(32)
        row.webhook_secret_encrypted = self.sealer.seal(secret)
        row.updated_at = now()
        self.db.flush()

        return secret

    def clear_oauth_app(self, provider: str) -> None:
        row = self.db.get(OAuthAppRow, provider)

        if row is not None:
            self.db.delete(row)
            self.db.flush()
