"""ImportSource ABC."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from action_platform_api.core.shared.credentials import Credentials


class ImportSource(ABC):
    """Where an app's releases and pull requests are read from: one per code host, answering in the platform's shape."""

    kind: str

    @abstractmethod
    def headers(self, creds: "Credentials") -> dict[str, str]:
        """The HTTP headers that authenticate `creds` on this host."""

    @abstractmethod
    def releases(self, creds: "Credentials", repo: str) -> list[dict[str, Any]]:
        """Every release of `repo` (owner/name): tag, name, body, url, author, sha, prerelease, draft, published_at, source."""

    @abstractmethod
    def pull_requests(self, creds: "Credentials", repo: str) -> list[dict[str, Any]]:
        """Every pull request of `repo`: number, title, url, author, head, base, state, draft, created_at, updated_at, merged_at, source."""
