"""The OAuth dance: signed state, authorize URL, code exchange, identity."""

from __future__ import annotations

import base64
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import urlencode

from action_platform.api.auth.secrets import Secrets
from action_platform.api.services.credentials import OAuthApp
from action_platform.api.services.http import basic, get_json, post_form
from action_platform.core.exception import ProviderError
from action_platform.api.services.hosts.providers import (
    PROVIDER_INFO,
    api_base_of,
    base_of,
    now,
)

STATE_TTL = 10 * 60


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


class OAuthState:
    """Signed, short-lived state for the OAuth round trip: organization, where to return, who started it."""

    def __init__(self, secrets: Secrets) -> None:
        self.key = secrets.subkey("oauth-state")

    def sign(self, organization_id: str, return_to: str, user_id: Optional[str]) -> str:
        payload = _b64(
            json.dumps(
                {
                    "orgId": organization_id,
                    "returnTo": return_to,
                    "userId": user_id,
                    "nonce": secrets.token_hex(8),
                    "ts": int(time.time() * 1000),
                },
                separators=(",", ":"),
            ).encode()
        )

        return f"{payload}.{self._mac(payload)}"

    def verify(
        self, raw: Optional[str], user_id: Optional[str]
    ) -> Optional[dict[str, Any]]:
        if not raw or "." not in raw:
            return None

        payload, _, mac = raw.rpartition(".")

        if not hmac.compare_digest(mac, self._mac(payload)):
            return None

        try:
            state = json.loads(_unb64(payload))
        except ValueError:
            return None

        if time.time() * 1000 - state.get("ts", 0) > STATE_TTL * 1000:
            return None

        if state.get("userId") and state["userId"] != user_id:
            return None

        return state

    def _mac(self, payload: str) -> str:
        return _b64(hmac.new(self.key, payload.encode(), "sha256").digest())


def callback_url(provider: str, origin: str) -> str:
    return f"{origin}/api/oauth/{provider}/callback"


def authorize_url(provider: str, app: OAuthApp, origin: str, state: str) -> str:
    params = {
        "client_id": app.client_id,
        "redirect_uri": callback_url(provider, origin),
        "state": state,
        "response_type": "code",
    }

    if PROVIDER_INFO[provider]["scopes"]:
        params["scope"] = PROVIDER_INFO[provider]["scopes"]

    if provider == "github":
        return f"{base_of(provider, app)}/login/oauth/authorize?{urlencode(params)}"

    if provider == "gitlab":
        return f"{base_of(provider, app)}/oauth/authorize?{urlencode(params)}"

    return f"https://bitbucket.org/site/oauth2/authorize?{urlencode(params)}"


def _token(data: dict[str, Any]) -> tuple[str, Optional[str], Optional[datetime]]:
    access = data.get("access_token")

    if not isinstance(access, str) or not access:
        raise ProviderError(
            str(
                data.get("error_description")
                or data.get("error")
                or "no access token in the provider's response"
            )
        )

    expires_in = data.get("expires_in")
    refresh = data.get("refresh_token")

    return (
        access,
        refresh if isinstance(refresh, str) else None,
        now() + timedelta(seconds=int(expires_in))
        if isinstance(expires_in, (int, float))
        else None,
    )


def exchange_code(
    provider: str, app: OAuthApp, origin: str, code: str
) -> tuple[str, Optional[str], Optional[datetime]]:
    redirect = callback_url(provider, origin)

    if provider == "github":
        return _token(
            post_form(
                f"{base_of(provider, app)}/login/oauth/access_token",
                {
                    "client_id": app.client_id,
                    "client_secret": app.client_secret,
                    "code": code,
                    "redirect_uri": redirect,
                },
            )
        )

    if provider == "gitlab":
        return _token(
            post_form(
                f"{base_of(provider, app)}/oauth/token",
                {
                    "client_id": app.client_id,
                    "client_secret": app.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect,
                },
            )
        )

    return _token(
        post_form(
            "https://bitbucket.org/site/oauth2/access_token",
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect,
            },
            {"authorization": basic(app.client_id, app.client_secret)},
        )
    )


def identity(
    provider: str, app: OAuthApp, access_token: str
) -> tuple[str, Optional[str]]:
    user = get_json(
        f"{api_base_of(provider, app)}/user",
        {"authorization": f"Bearer {access_token}"},
    )
    login = user.get("login") if provider == "github" else user.get("username")

    if not login:
        raise ProviderError(
            f"{PROVIDER_INFO[provider]['label']}: could not read the signed-in user"
        )

    return login, user.get("name") or user.get("display_name")
