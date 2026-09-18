"""Bitbucket Cloud SourceHost provider over the REST API 2.0 (username + app password, or an access token)."""

from __future__ import annotations

import re

import base64
from pathlib import Path

from action_platform.abc.source_host import SourceHost
from action_platform.core.context import Context, PRRef, ReleaseRef
from action_platform.core.exception import ProviderError
from action_platform.providers.source import rest
from action_platform.settings import settings


OAUTH_USERNAME = "x-token-auth"


class SourceBitbucket(SourceHost):
    """
    Args:
        repo (str): "workspace/name".
        token (str | None): app password (with `username`) or a workspace/repository access token.
        username (str | None): Bitbucket username when `token` is an app password.
        base_url (str | None): unused for Cloud; kept for symmetry.
    """

    name = "bitbucket"

    def __init__(
        self,
        repo: str,
        token: str | None = None,
        username: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.repo = repo
        self.token = token or settings.BITBUCKET_TOKEN
        self.username = username or settings.BITBUCKET_USERNAME
        self.api = "https://api.bitbucket.org/2.0"
        self.web = "https://bitbucket.org"

    def _require_credentials(self) -> None:
        if not self.token:
            raise ProviderError(
                "no Bitbucket credentials for this repository: on the platform, connect a Bitbucket "
                "host in Settings; on the CLI, set ACTION_PLATFORM_BITBUCKET_TOKEN"
            )

    def _headers(self) -> dict[str, str]:
        """An app password goes as Basic with the username; an OAuth access token (username `x-token-auth`, the name git uses for it) goes as Bearer — Basic with that pseudo-user answers 401 on the REST API."""
        if self.username and self.username != OAUTH_USERNAME:
            raw = base64.b64encode(f"{self.username}:{self.token}".encode()).decode()

            return {"authorization": f"Basic {raw}"}

        return {"authorization": f"Bearer {self.token}"}

    def _rest(self, method: str, path: str, body: dict | None = None):
        self._require_credentials()

        return rest.call(method, f"{self.api}{path}", self._headers(), body)

    def detect(self, remote_url: str) -> bool:
        return "bitbucket.org" in remote_url

    def create_repository(
        self, repo: str, description: str = "", private: bool = False
    ) -> str:
        workspace, name = repo.split("/", 1)

        try:
            self._rest(
                "POST",
                f"/repositories/{workspace}/{name}",
                {"scm": "git", "is_private": private, "description": description},
            )
        except ProviderError as e:
            if "already" not in str(e):
                raise

        return f"{self.web}/{repo}.git"

    def delete_repository(self, repo: str) -> None:
        try:
            self._rest("DELETE", f"/repositories/{repo}")
        except ProviderError as e:
            if "→ 404" not in str(e):
                raise

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
        name: str | None = None,
        latest: bool = True,
    ) -> ReleaseRef:
        return ReleaseRef(id=tag, tag=tag, url=f"{self.web}/{self.repo}/src/{tag}/")

    def open_pr(
        self,
        ctx: Context,
        base: str,
        head: str,
        title: str,
        body: str,
        draft: bool = False,
    ) -> PRRef:
        data = self._rest(
            "POST",
            f"/repositories/{self.repo}/pullrequests",
            {
                "title": title,
                "description": body,
                "source": {"branch": {"name": head}},
                "destination": {"branch": {"name": base}},
                "close_source_branch": True,
            },
        )

        return PRRef(number=data["id"], url=data["links"]["html"]["href"])

    def releases(self, repo: str) -> list[dict]:
        return [
            {
                "tag": r["name"],
                "name": r["name"],
                "body": r.get("message"),
                "url": ((r.get("links") or {}).get("html") or {}).get("href")
                or f"{self.web}/{repo}/src/{r['name']}/",
                "author": (
                    ((r.get("target") or {}).get("author") or {}).get("user") or {}
                ).get("display_name"),
                "sha": ((r.get("target") or {}).get("hash") or "")[:7] or None,
                "prerelease": bool(RC.search(r["name"])),
                "draft": False,
                "published_at": rest.parse_utc((r.get("target") or {}).get("date")),
                "source": "bitbucket",
            }
            for r in rest.get_values(
                f"{self.api}/repositories/{repo}/refs/tags?sort=-target.date&pagelen=100",
                self._headers(),
            )
        ]

    def pull_requests(self, repo: str) -> list[dict]:
        return [
            {
                "number": r["id"],
                "title": r["title"],
                "url": ((r.get("links") or {}).get("html") or {}).get("href")
                or f"{self.web}/{repo}/pull-requests/{r['id']}",
                "author": (r.get("author") or {}).get("display_name"),
                "head": r["source"]["branch"]["name"],
                "base": r["destination"]["branch"]["name"],
                "state": "merged"
                if r.get("state") == "MERGED"
                else "open"
                if r.get("state") == "OPEN"
                else "closed",
                "draft": False,
                "created_at": rest.parse_utc(r["created_on"]),
                "updated_at": rest.parse_utc(r["updated_on"]),
                "merged_at": rest.parse_utc(r["updated_on"])
                if r.get("state") == "MERGED"
                else None,
                "source": "bitbucket",
            }
            for r in rest.get_values(
                f"{self.api}/repositories/{repo}/pullrequests?state=OPEN&state=MERGED&state=DECLINED&sort=-updated_on&pagelen=50",
                self._headers(),
            )
        ]


RC = re.compile(r"-rc\.")
