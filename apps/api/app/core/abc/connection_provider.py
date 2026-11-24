"""ConnectionProvider ABC: a service the organization connects with OAuth that is not a code host — its authorize and token endpoints, and what a grant comes back with."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.core.shared.credentials import OAuthApp


@dataclass(frozen=True)
class TokenGrant:
    """What the provider's token endpoint answered: the tokens, when they expire, the scopes granted and who granted them."""

    access: str
    refresh: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: Optional[tuple[str, ...]] = None
    login: str = ""


class ConnectionProvider(ABC):
    kind: str
    label: str
    scopes: str
    callback_hint: str

    @abstractmethod
    def api_base(self, app: "OAuthApp") -> str:
        """Where the service's REST API lives for this OAuth app (self-hosted instances included)."""

    @abstractmethod
    def authorize_url(
        self, app: "OAuthApp", origin: str, state: str, scopes: str
    ) -> str:
        """Where the browser goes to grant `scopes`."""

    @abstractmethod
    def exchange_code(self, app: "OAuthApp", origin: str, code: str) -> TokenGrant:
        """Trade the callback code for a grant."""

    @abstractmethod
    def refresh(self, app: "OAuthApp", refresh_token: str) -> TokenGrant:
        """Trade a refresh token for a new grant."""

    def stored_base_url(self, app: "OAuthApp") -> Optional[str]:
        """The API base to keep on the connection, None for the public instance."""
        return self.api_base(app) if app.base_url else None

    def callback_url(self, origin: str) -> str:
        return f"{origin}/api/oauth/{self.kind}/callback"
