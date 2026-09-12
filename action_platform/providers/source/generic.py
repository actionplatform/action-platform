"""Any other git server: pushes and tags work, nothing else does."""

from __future__ import annotations

from pathlib import Path

from action_platform.abc.source_host import SourceHost
from action_platform.core.context import Context, PRRef, ReleaseRef


class SourceGeneric(SourceHost):
    """
    Args:
        repo (str): "owner/name", informational.
        base_url (str): where the repository lives, e.g. https://git.example.com/owner/name.git.
    """

    name = "generic"

    def __init__(
        self,
        repo: str,
        token: str | None = None,
        username: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.repo = repo
        self.token = token
        self.username = username
        self.base_url = (base_url or "").rstrip("/")

    def detect(self, remote_url: str) -> bool:
        return bool(self.base_url) and self.base_url in remote_url

    def create_tag(self, ctx: Context, tag: str) -> None:
        return None

    def create_release(
        self,
        ctx: Context,
        tag: str,
        notes: str,
        assets: list[Path] | None = None,
        draft: bool = False,
        prerelease: bool = False,
    ) -> ReleaseRef:
        return ReleaseRef(id=tag, tag=tag, url=f"{self.base_url}#{tag}")

    def open_pr(
        self,
        ctx: Context,
        base: str,
        head: str,
        title: str,
        body: str,
        draft: bool = False,
    ) -> PRRef:
        raise NotImplementedError(
            "generic hosts cannot open pull requests; push the branch and open it by hand"
        )
