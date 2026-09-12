"""GitHub SourceHost provider (gh CLI)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from action_platform.abc.source_host import SourceHost
from action_platform.core.context import Context, PRRef, ReleaseRef
from action_platform.core.exception import ProviderError


class SourceGithub(SourceHost):
    """
    Import:
        from action_platform.providers import SourceGithub

    Example:
        SourceGithub(repo="owner/my-project")

    Args:
        repo (str): "owner/name".
    """

    name = "github"

    def __init__(self, repo: str) -> None:
        self.repo = repo
        if not shutil.which("gh"):
            raise ProviderError("gh CLI not found. Install: https://cli.github.com")

    def _gh(self, *args: str) -> str:
        result = subprocess.run(
            ["gh", *args, "--repo", self.repo],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise ProviderError(f"gh failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def detect(self, remote_url: str) -> bool:
        return "github.com" in remote_url

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
        args = ["release", "create", tag, "--title", tag, "--notes", notes]
        if draft:
            args.append("--draft")
        if prerelease:
            args.append("--prerelease")
        if assets:
            args.extend(str(a) for a in assets)
        url = self._gh(*args)

        view = self._gh("release", "view", tag, "--json", "url")
        data = json.loads(view)
        return ReleaseRef(id=tag, tag=tag, url=data.get("url", url))

    def open_pr(
        self, ctx: Context, base: str, head: str, title: str, body: str
    ) -> PRRef:
        url = self._gh(
            "pr",
            "create",
            "--base",
            base,
            "--head",
            head,
            "--title",
            title,
            "--body",
            body,
        )
        view = self._gh("pr", "view", url, "--json", "number")
        data = json.loads(view)
        return PRRef(number=data["number"], url=url)
