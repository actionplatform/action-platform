"""Code-host credentials and the OAuth apps they come from."""

from dataclasses import dataclass, replace
from typing import Optional

from action_platform.core.exception import ActionPlatformError
from action_platform.core.origin import Origin
from action_platform.settings import settings

PUBLIC_HOSTS = {
    "github": "https://github.com",
    "gitlab": "https://gitlab.com",
    "bitbucket": "https://bitbucket.org",
}
API_HOSTS = {"api.github.com": "github.com", "api.bitbucket.org": "bitbucket.org"}


class CredentialsError(ActionPlatformError):
    pass


def connection_origin(kind: Optional[str], base_url: Optional[str]) -> Optional[Origin]:
    """The one origin a connection's token is good for: its base URL's, else the public instance of its kind; None when neither names one, so the token goes nowhere."""
    origin = Origin.parse(base_url if base_url else PUBLIC_HOSTS.get(kind or ""))

    if origin is not None and origin.host in API_HOSTS:
        return replace(origin, host=API_HOSTS[origin.host])

    return origin


@dataclass(frozen=True)
class Credentials:
    kind: str
    token: str
    username: Optional[str]
    base_url: Optional[str]
    owner: Optional[str]

    @property
    def origin(self) -> Optional[Origin]:
        return connection_origin(self.kind, self.base_url)

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

    @classmethod
    def from_env(cls, kind: str) -> Optional["OAuthApp"]:
        """The app configured through AP_<KIND>_CLIENT_ID / _CLIENT_SECRET / _BASE_URL (or without the AP_ prefix), if any."""
        prefix = kind.upper()
        client_id = settings.env(f"AP_{prefix}_CLIENT_ID") or settings.env(
            f"{prefix}_CLIENT_ID"
        )
        client_secret = settings.env(f"AP_{prefix}_CLIENT_SECRET") or settings.env(
            f"{prefix}_CLIENT_SECRET"
        )

        if not client_id or not client_secret:
            return None

        return cls(
            client_id,
            client_secret,
            settings.env(f"AP_{prefix}_BASE_URL") or settings.env(f"{prefix}_BASE_URL"),
        )
