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
        CommitRow,
        Context,
        PRRef,
        PullRequestRow,
        ReleaseRef,
        ReleaseRow,
        TagRow,
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


@runtime_checkable
class ReadsRepository(Protocol):
    """A host that answers what a clone would: commits and files at a ref."""

    def commits(
        self, repo: str, ref: str, limit: int = 50, path: str | None = None
    ) -> "list[CommitRow]":
        """The last `limit` commits reachable from `ref`, newest first; with `path`, only those that touch it."""

    def compare(self, repo: str, base: str, head: str) -> "list[CommitRow]":
        """The commits on `head` that `base` does not have, newest first."""

    def file(self, repo: str, ref: str, path: str) -> str | None:
        """The text of `path` at `ref`; None when it is not there."""

    def tags(self, repo: str) -> "list[TagRow]":
        """Every tag, newest first."""
