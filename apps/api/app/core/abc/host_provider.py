"""HostProvider ABC and the access report every provider answers with."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.core.shared.credentials import Credentials, OAuthApp


@dataclass
class Owner:
    """An account, installation or workspace the token may create repositories in."""

    account: str
    kind: str
    repositories: str
    administration: str
    contents: str
    actions: str = "none"
    selected: Optional[list[str]] = None
    configure_url: Optional[str] = None

    @property
    def can_create_repos(self) -> bool:
        return self.administration == "write" and self.contents == "write"

    def as_dict(self) -> dict[str, Any]:
        return {
            "account": self.account,
            "kind": self.kind,
            "repositories": self.repositories,
            "administration": self.administration,
            "contents": self.contents,
            "actions": self.actions,
            "canCreateRepos": self.can_create_repos,
            "selected": self.selected,
            "configureUrl": self.configure_url,
        }


@dataclass
class AccessReport:
    """What a connected account may create with, or why the host refused the token."""

    kind: str
    login: str
    installations: list[Owner] = field(default_factory=list)
    install_url: Optional[str] = None
    problems: list[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def as_dict(self) -> dict[str, Any]:
        if self.error is not None:
            return {"ok": False, "error": self.error}

        return {
            "ok": True,
            "kind": self.kind,
            "login": self.login,
            "installations": [o.as_dict() for o in self.installations],
            "installUrl": self.install_url,
            "problems": self.problems,
        }

    @classmethod
    def refused(cls, kind: str, label: str, status: int) -> "AccessReport":
        return cls(
            kind=kind,
            login="",
            error=f"token rejected by {label} ({status}); reconnect the host",
        )


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
    def access(self, creds: "Credentials", app_slug: Optional[str]) -> AccessReport:
        """What the connected account may create with: accounts, installations or workspaces, with what is wrong about each."""

    def callback_url(self, origin: str) -> str:
        return f"{origin}/api/oauth/{self.kind}/callback"
