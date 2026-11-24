"""Sentry: an API application's authorization code grant, on sentry.io or a self-hosted instance."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from app.core.abc import ConnectionProvider, TokenGrant
from app.core.shared.credentials import OAuthApp
from app.core.shared.http import http
from app.services.integrations.hosts.tokens import TokenResponse

SENTRY_URL = "https://sentry.io"


class SentryProvider(ConnectionProvider):
    kind = "sentry"
    label = "Sentry"
    scopes = "org:read"
    callback_hint = "Sentry → User settings → API → Applications → Create New Application (Confidential)"

    def web_base(self, app: OAuthApp) -> str:
        return (app.base_url or SENTRY_URL).rstrip("/").removesuffix("/api/0")

    def api_base(self, app: OAuthApp) -> str:
        return f"{self.web_base(app)}/api/0"

    def authorize_url(self, app: OAuthApp, origin: str, state: str, scopes: str) -> str:
        params = {
            "client_id": app.client_id,
            "redirect_uri": self.callback_url(origin),
            "response_type": "code",
            "state": state,
            "scope": scopes,
        }

        return f"{self.web_base(app)}/oauth/authorize/?{urlencode(params)}"

    def exchange_code(self, app: OAuthApp, origin: str, code: str) -> TokenGrant:
        return self._grant(
            self._token(
                app,
                {
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.callback_url(origin),
                },
            )
        )

    def refresh(self, app: OAuthApp, refresh_token: str) -> TokenGrant:
        return self._grant(
            self._token(
                app, {"grant_type": "refresh_token", "refresh_token": refresh_token}
            )
        )

    def _token(self, app: OAuthApp, form: dict[str, str]) -> dict[str, Any]:
        return http.post_form(
            f"{self.web_base(app)}/oauth/token/",
            {"client_id": app.client_id, "client_secret": app.client_secret, **form},
        )

    @staticmethod
    def _grant(data: dict[str, Any]) -> TokenGrant:
        access, refresh, expires_at = TokenResponse(data).read()
        scope = data.get("scope")
        scopes = (
            tuple(scope.split())
            if isinstance(scope, str)
            else tuple(str(s) for s in scope)
            if isinstance(scope, list)
            else None
        )
        user = data.get("user") if isinstance(data.get("user"), dict) else {}

        return TokenGrant(
            access,
            refresh,
            expires_at,
            scopes,
            str(user.get("email") or user.get("name") or user.get("id") or ""),
        )
