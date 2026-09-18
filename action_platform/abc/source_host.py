"""SourceHost ABC."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from action_platform.core.context import Context, PRRef, ReleaseRef


class SourceHost(ABC):
    """SourceHost"""

    name: str

    @abstractmethod
    def detect(self, remote_url: str) -> bool:
        """Return True if this provider handles remote_url."""

    def create_repository(
        self, repo: str, description: str = "", private: bool = False
    ) -> str:
        """Create the remote repository; return its clone URL."""
        raise NotImplementedError(f"{self.name} cannot create repositories")

    def delete_repository(self, repo: str) -> None:
        """Delete the remote repository; a repository that is already gone is not an error."""
        raise NotImplementedError(f"{self.name} cannot delete repositories")

    @abstractmethod
    def create_tag(self, ctx: "Context", tag: str) -> None:
        """Create annotated tag on remote."""

    @abstractmethod
    def create_release(
        self,
        ctx: "Context",
        tag: str,
        notes: str,
        assets: list[Path] | None = None,
        draft: bool = False,
        prerelease: bool = False,
        name: str | None = None,
        latest: bool = True,
    ) -> "ReleaseRef":
        """Publish release on remote host. `name` titles it (the tag otherwise); `latest` says whether the host should mark it as the latest one."""

    def releases(self, repo: str) -> list[dict]:
        """The releases the host publishes for `repo`, newest first: tag, name, body, url, author, sha, prerelease, draft, published_at, source."""
        raise NotImplementedError(f"{self.name} does not publish releases")

    def pull_requests(self, repo: str) -> list[dict]:
        """The pull (merge) requests of `repo`: number, title, url, author, head, base, state (open|merged|closed), draft, created_at, updated_at, merged_at, source."""
        raise NotImplementedError(f"{self.name} does not know pull requests")

    @abstractmethod
    def open_pr(
        self,
        ctx: "Context",
        base: str,
        head: str,
        title: str,
        body: str,
        draft: bool = False,
    ) -> "PRRef":
        """Open pull/merge request."""
