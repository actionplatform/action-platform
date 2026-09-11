"""SourceHost ABC."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devtool.core.context import Context, PRRef, ReleaseRef


class SourceHost(ABC):
    """SourceHost"""

    name: str

    @abstractmethod
    def detect(self, remote_url: str) -> bool:
        """Return True if this provider handles remote_url."""

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
    ) -> "ReleaseRef":
        """Publish release on remote host."""

    @abstractmethod
    def open_pr(
        self,
        ctx: "Context",
        base: str,
        head: str,
        title: str,
        body: str,
    ) -> "PRRef":
        """Open pull/merge request."""
