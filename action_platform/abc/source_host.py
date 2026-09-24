"""SourceHost ABC and the capability protocols a host may add to it.

Every host detects its remotes, tags, publishes releases and opens pull
requests. Creating and deleting repositories, listing releases and listing
pull requests vary by host: a host that offers one implements the matching
protocol, and callers ask with `isinstance` instead of catching an error.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from action_platform.core.context import (
        Context,
        PRRef,
        PullRequestRow,
        ReleaseRef,
        ReleaseRow,
    )


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
        name: str | None = None,
        latest: bool = True,
    ) -> "ReleaseRef":
        """Publish release on remote host. `name` titles it (the tag otherwise); `latest` says whether the host should mark it as the latest one."""

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


@runtime_checkable
class SupportsRepoCreation(Protocol):
    """A host that creates repositories."""

    def create_repository(
        self, repo: str, description: str = "", private: bool = False
    ) -> str:
        """Create the remote repository; return its clone URL."""


@runtime_checkable
class SupportsRepoDeletion(Protocol):
    """A host that deletes repositories."""

    def delete_repository(self, repo: str) -> None:
        """Delete the remote repository; a repository that is already gone is not an error."""


@runtime_checkable
class PublishesReleases(Protocol):
    """A host that lists the releases it publishes."""

    def releases(self, repo: str) -> "list[ReleaseRow]":
        """The releases the host publishes for `repo`, newest first."""


@runtime_checkable
class ListsPullRequests(Protocol):
    """A host that lists pull (merge) requests."""

    def pull_requests(self, repo: str) -> "list[PullRequestRow]":
        """The pull (merge) requests of `repo`."""
