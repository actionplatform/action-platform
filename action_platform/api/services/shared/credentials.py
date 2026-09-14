"""Code-host credentials and the OAuth apps that refresh them."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from action_platform.api.services.shared.common import now
from action_platform.core.exception import ActionPlatformError
from action_platform.api.services.shared.http import basic, post_form
from action_platform.settings import settings


class CredentialsError(ActionPlatformError):
    pass


@dataclass(frozen=True)
class Credentials:
    kind: str
    token: str
    username: Optional[str]
    base_url: Optional[str]
    owner: Optional[str]

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "token": self.token,
            "username": self.username,
            "base_url": self.base_url,
            "owner": self.owner,
        }


@dataclass(frozen=True)
class OAuthApp:
    client_id: str
    client_secret: str
    base_url: Optional[str]
    slug: Optional[str] = None


def oauth_app_for(kind: str) -> Optional[OAuthApp]:
    prefix = kind.upper()
    client_id = settings.env(f"AP_{prefix}_CLIENT_ID") or settings.env(
        f"{prefix}_CLIENT_ID"
    )
    client_secret = settings.env(f"AP_{prefix}_CLIENT_SECRET") or settings.env(
        f"{prefix}_CLIENT_SECRET"
    )

    if not client_id or not client_secret:
        return None

    return OAuthApp(
        client_id,
        client_secret,
        settings.env(f"AP_{prefix}_BASE_URL") or settings.env(f"{prefix}_BASE_URL"),
    )


def refresh_oauth(
    app: Optional[OAuthApp], kind: str, refresh_token: str
) -> tuple[str, Optional[str], Optional[datetime]]:
    if app is None:
        raise CredentialsError(
            f"the {kind} token expired and no OAuth app is configured on the API to refresh it"
        )

    if kind == "gitlab":
        base = (app.base_url or "https://gitlab.com").rstrip("/")
        data = post_form(
            f"{base}/oauth/token",
            {
                "client_id": app.client_id,
                "client_secret": app.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
    elif kind == "bitbucket":
        data = post_form(
            "https://bitbucket.org/site/oauth2/access_token",
            {"grant_type": "refresh_token", "refresh_token": refresh_token},
            {"authorization": basic(app.client_id, app.client_secret)},
        )
    else:
        base = re.sub(
            r"/api/v3$", "", (app.base_url or "https://github.com").rstrip("/")
        )
        data = post_form(
            f"{base}/login/oauth/access_token",
            {
                "client_id": app.client_id,
                "client_secret": app.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )

    access = data.get("access_token")

    if not isinstance(access, str) or not access:
        raise CredentialsError("no access token in the provider's response")

    expires_in = data.get("expires_in")
    expires_at = (
        now() + timedelta(seconds=int(expires_in))
        if isinstance(expires_in, (int, float))
        else None
    )
    refreshed = data.get("refresh_token")

    return access, refreshed if isinstance(refreshed, str) else None, expires_at
