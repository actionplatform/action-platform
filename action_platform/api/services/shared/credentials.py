"""Code-host credentials and the OAuth apps they come from."""

from dataclasses import dataclass
from typing import Optional

from action_platform.core.exception import ActionPlatformError
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
