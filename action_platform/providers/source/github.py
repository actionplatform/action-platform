"""GitHub SourceHost provider.

With a token it talks to the REST API (github.com or GitHub Enterprise via
`base_url`); without one it falls back to the `gh` CLI and whatever that is
logged in as.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from action_platform.abc.source_host import SourceHost
from action_platform.core.context import Context, PRRef, ReleaseRef
from action_platform.core.exception import ProviderError
from action_platform.providers.source import rest
from action_platform.settings import settings


class SourceGithub(SourceHost):
    """
    Import:
        from action_platform.providers import SourceGithub

    Example:
        SourceGithub(repo="owner/my-project", token="ghp_…")

    Args:
        repo (str): "owner/name".
        token (str | None): personal access or app token; default from ACTION_PLATFORM_GITHUB_TOKEN / GH_TOKEN, else the gh CLI.
        base_url (str | None): API root for GitHub Enterprise, e.g. https://ghe.example.com/api/v3.
    """

    name = "github"

    def __init__(
        self, repo: str, token: str | None = None, base_url: str | None = None
    ) -> None:
        self.repo = repo
        self.token = token or settings.GITHUB_TOKEN
        self.api = (base_url or "https://api.github.com").rstrip("/")
        self.web = (
            "https://github.com"
            if self.api == "https://api.github.com"
            else self.api.removesuffix("/api/v3")
        )

        if not self.token and not shutil.which("gh"):
            raise ProviderError(
                "no GitHub token and no gh CLI: set ACTION_PLATFORM_GITHUB_TOKEN or install https://cli.github.com"
            )

    def _rest(self, method: str, path: str, body: dict | None = None):
        return rest.call(
            method,
            f"{self.api}{path}",
            {
                "authorization": f"Bearer {self.token}",
                "x-github-api-version": "2022-11-28",
            },
            body,
        )

    def _existing_pr(self, head: str) -> dict:
        owner = self.repo.split("/")[0]
        rows = self._rest(
            "GET",
            f"/repos/{self.repo}/pulls?state=open&head={owner}:{head}",
        )

        if not rows:
            raise ProviderError(f"a pull request for {head} exists but was not found")

        return rows[0]

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
        return "github.com" in remote_url or self.web in remote_url

    def create_repository(
        self, repo: str, description: str = "", private: bool = False
    ) -> str:
        owner, name = repo.split("/", 1)

        if self.token:
            body = {"name": name, "description": description, "private": private}
            me = self._rest("GET", "/user")
            path = "/user/repos" if me.get("login") == owner else f"/orgs/{owner}/repos"

            try:
                self._rest("POST", path, body)
            except ProviderError as e:
                if "already exists" not in str(e):
                    raise

            return f"{self.web}/{repo}.git"

        args = ["gh", "repo", "create", repo, "--private" if private else "--public"]

        if description:
            args += ["--description", description]

        result = subprocess.run(args, check=False, capture_output=True, text=True)

        if result.returncode != 0:
            raise ProviderError(f"gh repo create failed: {result.stderr.strip()}")

        return f"https://github.com/{repo}.git"

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
        if self.token:
            data = self._rest(
                "POST",
                f"/repos/{self.repo}/releases",
                {
                    "tag_name": tag,
                    "name": tag,
                    "body": notes,
                    "draft": draft,
                    "prerelease": prerelease,
                },
            )

            return ReleaseRef(id=str(data["id"]), tag=tag, url=data["html_url"])

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
        self,
        ctx: Context,
        base: str,
        head: str,
        title: str,
        body: str,
        draft: bool = False,
    ) -> PRRef:
        if self.token:
            try:
                data = self._rest(
                    "POST",
                    f"/repos/{self.repo}/pulls",
                    {
                        "base": base,
                        "head": head,
                        "title": title,
                        "body": body,
                        "draft": draft,
                    },
                )
            except ProviderError as e:
                if "already exists" not in str(e):
                    raise
                data = self._existing_pr(head)

            return PRRef(number=data["number"], url=data["html_url"])

        args = [
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
        ]

        if draft:
            args.append("--draft")

        url = self._gh(*args)
        view = self._gh("pr", "view", url, "--json", "number")
        data = json.loads(view)

        return PRRef(number=data["number"], url=url)
