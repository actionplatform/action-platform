"""GitHub SourceHost provider (gh CLI)."""

from __future__ import annotations

from pathlib import Path

from devtool.abc.source_host import SourceHost
from devtool.core.context import Context, PRRef, ReleaseRef


class SourceGithub(SourceHost):
    """
    Import:
        from devtool.providers import SourceGithub

    Example:
        SourceGithub(repo="owner/my-project")

    Args:
        repo (str): "owner/name".
    """

    name = "github"

    def __init__(self, repo: str) -> None:
        self.repo = repo

    def detect(self, remote_url: str) -> bool:
        return "github.com" in remote_url

    def create_tag(self, ctx: Context, tag: str) -> None:
        raise NotImplementedError

    def create_release(
        self,
        ctx: Context,
        tag: str,
        notes: str,
        assets: list[Path] | None = None,
        draft: bool = False,
        prerelease: bool = False,
    ) -> ReleaseRef:
        raise NotImplementedError

    def open_pr(self, ctx: Context, base: str, head: str, title: str, body: str) -> PRRef:
        raise NotImplementedError
