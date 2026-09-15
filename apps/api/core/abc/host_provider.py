"""HostProvider ABC."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from action_platform_api.core.shared.credentials import Credentials, OAuthApp


class HostProvider(ABC):
    """A code host the platform connects organizations to: how its OAuth flow works, where its API lives, and what a connected account may create with."""

    kind: str
    label: str
    scopes: str
    callback_hint: str

    @abstractmethod
    def web_base(self, app: "OAuthApp") -> str:
        """Where the host's web UI lives for this OAuth app (self-hosted instances included)."""

    @abstractmethod
    def api_base(self, app: "OAuthApp") -> str:
        """Where the host's REST API lives for this OAuth app."""

    @abstractmethod
    def stored_base_url(self, app: "OAuthApp") -> Optional[str]:
        """The base URL to keep on a connected host, None for the public instance."""

    @abstractmethod
    def authorize_url(self, app: "OAuthApp", origin: str, state: str) -> str:
        """Where the browser goes to grant access."""

    @abstractmethod
    def exchange_code(
        self, app: "OAuthApp", origin: str, code: str
    ) -> tuple[str, Optional[str], Optional[datetime]]:
        """Trade the callback code for (access token, refresh token, expiry)."""

    @abstractmethod
    def refresh(
        self, app: "OAuthApp", refresh_token: str
    ) -> tuple[str, Optional[str], Optional[datetime]]:
        """Trade a refresh token for a new (access token, refresh token, expiry)."""

    @abstractmethod
    def identity(self, app: "OAuthApp", access_token: str) -> tuple[str, Optional[str]]:
        """(login, display name) of the account behind the token."""

    @abstractmethod
    def access(self, creds: "Credentials", app_slug: Optional[str]) -> dict[str, Any]:
        """What the connected account may create with: accounts, installations or workspaces, with what is wrong about each."""

    def callback_url(self, origin: str) -> str:
        return f"{origin}/api/oauth/{self.kind}/callback"
