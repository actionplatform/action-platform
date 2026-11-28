"""GitLab SourceHost provider over the REST API v4 (gitlab.com or self-hosted via `base_url`)."""

from __future__ import annotations

from datetime import datetime

import base64
import re

import urllib.parse
from pathlib import Path

from action_platform.abc.source_host import SourceHost
from action_platform.core.context import (
    CommitRow,
    Context,
    PRRef,
    PullRequestRow,
    ReleaseRef,
    ReleaseRow,
    TagRow,
)
from action_platform.core.exception import ProviderError
from action_platform.providers.source import rest


class SourceGitlab(SourceHost):
    """
    Args:
        repo (str): "group/name" (subgroups allowed: "group/sub/name").
        token (str | None): personal / project / group access token.
        base_url (str | None): instance root, e.g. https://gitlab.example.com (default https://gitlab.com).
    """

    name = "gitlab"

    def __init__(
        self, repo: str, token: str | None = None, base_url: str | None = None
    ) -> None:
        self.repo = repo
        self.token = token
        self.web = (base_url or "https://gitlab.com").rstrip("/")
        self.api = f"{self.web}/api/v4"

    def _require_credentials(self) -> None:
        if not self.token:
            raise ProviderError(
                "no GitLab credentials for this repository: on the platform, connect a GitLab host "
                "in Settings; on the CLI, set ACTION_PLATFORM_GITLAB_TOKEN"
            )

    @property
    def _id(self) -> str:
        return urllib.parse.quote(self.repo, safe="")

    def _rest(self, method: str, path: str, body: dict | None = None):
        self._require_credentials()

        return rest.call(
            method,
            f"{self.api}{path}",
            {"authorization": f"Bearer {self.token}"},
            body,
        )

    def detect(self, remote_url: str) -> bool:
        return "gitlab.com" in remote_url or self.web in remote_url

    def create_repository(
        self, repo: str, description: str = "", private: bool = False
    ) -> str:
        namespace, name = repo.rsplit("/", 1)
        body = {
            "name": name,
            "path": name,
            "description": description,
            "visibility": "private" if private else "public",
            "initialize_with_readme": False,
        }
        me = self._rest("GET", "/user")

        if me.get("username") != namespace:
            group = self._rest(
                "GET", f"/groups/{urllib.parse.quote(namespace, safe='')}"
            )
            body["namespace_id"] = group["id"]

        try:
            data = self._rest("POST", "/projects", body)
        except ProviderError as e:
            if "has already been taken" not in str(e):
                raise
            data = {}

        return data.get("http_url_to_repo") or f"{self.web}/{repo}.git"

    def delete_repository(self, repo: str) -> None:
        try:
            self._rest("DELETE", f"/projects/{urllib.parse.quote(repo, safe='')}")
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
        if prerelease:
            notes = f"_Pre-release_\n\n{notes}"

        data = self._rest(
            "POST",
            f"/projects/{self._id}/releases",
            {"tag_name": tag, "name": name or tag, "description": notes},
        )

        return ReleaseRef(
            id=tag,
            tag=tag,
            url=data.get("_links", {}).get(
                "self", f"{self.web}/{self.repo}/-/releases/{tag}"
            ),
        )

    def open_pr(
        self,
        ctx: Context,
        base: str,
        head: str,
        title: str,
        body: str,
        draft: bool = False,
    ) -> PRRef:
        try:
            data = self._rest(
                "POST",
                f"/projects/{self._id}/merge_requests",
                {
                    "source_branch": head,
                    "target_branch": base,
                    "title": f"Draft: {title}" if draft else title,
                    "description": body,
                },
            )
        except ProviderError as e:
            if "already exists" not in str(e):
                raise
            rows = self._rest(
                "GET",
                f"/projects/{self._id}/merge_requests?state=opened&source_branch={head}",
            )
            if not rows:
                raise
            data = rows[0]

        return PRRef(number=data["iid"], url=data["web_url"])

    def releases(self, repo: str) -> list[ReleaseRow]:
        headers = {"authorization": f"Bearer {self.token}"} if self.token else {}

        return [
            ReleaseRow(
                tag=r["tag_name"],
                name=r.get("name"),
                body=r.get("description"),
                url=((r.get("_links") or {}).get("self"))
                or f"{self.web}/{repo}/-/releases/{r['tag_name']}",
                author=(r.get("author") or {}).get("username"),
                sha=((r.get("commit") or {}).get("id") or "")[:7] or None,
                prerelease=bool(r.get("upcoming_release"))
                or bool(RC.search(r["tag_name"])),
                draft=False,
                published_at=rest.parse_utc(
                    r.get("released_at") or r.get("created_at")
                ),
                source="gitlab",
            )
            for r in rest.get_pages(
                f"{self.api}/projects/{urllib.parse.quote(repo, safe='')}/releases",
                headers,
            )
        ]

    def pull_requests(
        self, repo: str, since: datetime | None = None
    ) -> list[PullRequestRow]:
        headers = {"authorization": f"Bearer {self.token}"} if self.token else {}

        return [
            PullRequestRow(
                number=r["iid"],
                title=r["title"],
                url=r["web_url"],
                author=(r.get("author") or {}).get("username"),
                head=r["source_branch"],
                base=r["target_branch"],
                state="merged"
                if r.get("state") == "merged"
                else "open"
                if r.get("state") == "opened"
                else "closed",
                draft=bool(r.get("draft")),
                created_at=rest.parse_utc(r["created_at"]),
                updated_at=rest.parse_utc(r["updated_at"]),
                merged_at=rest.parse_utc(r.get("merged_at")),
                source="gitlab",
            )
            for r in rest.get_pages(
                f"{self.api}/projects/{urllib.parse.quote(repo, safe='')}/merge_requests?state=all&order_by=updated_at",
                headers,
                10,
                enough=rest.older_than(since, "updated_at"),
            )
        ]

    def _read_headers(self) -> dict[str, str]:
        return {"authorization": f"Bearer {self.token}"} if self.token else {}

    def _project_api(self, repo: str) -> str:
        return f"{self.api}/projects/{urllib.parse.quote(repo, safe='')}/repository"

    def commits(
        self, repo: str, ref: str, limit: int = 50, path: str | None = None
    ) -> list[CommitRow]:
        only = f"&path={urllib.parse.quote(path)}" if path else ""
        rows = rest.call(
            "GET",
            f"{self._project_api(repo)}/commits?ref_name={urllib.parse.quote(ref, safe='')}&per_page={max(1, min(limit, 100))}{only}",
            self._read_headers(),
        )

        return [_commit(r) for r in rows or []][:limit]

    def compare(self, repo: str, base: str, head: str) -> list[CommitRow]:
        data = rest.call(
            "GET",
            f"{self._project_api(repo)}/compare?from={urllib.parse.quote(base, safe='')}&to={urllib.parse.quote(head, safe='')}",
            self._read_headers(),
        )

        return [_commit(r) for r in reversed((data or {}).get("commits") or [])]

    def file(self, repo: str, ref: str, path: str) -> str | None:
        try:
            data = rest.call(
                "GET",
                f"{self._project_api(repo)}/files/{urllib.parse.quote(path, safe='')}?ref={urllib.parse.quote(ref, safe='')}",
                self._read_headers(),
            )
        except rest.Missing:
            return None

        if not isinstance(data, dict):
            return None

        return base64.b64decode(data.get("content") or "").decode(errors="replace")

    def tags(self, repo: str) -> list[TagRow]:
        return [
            TagRow(
                name=r["name"],
                sha=(r.get("commit") or {}).get("id") or r.get("target") or "",
                date=rest.parse_utc(
                    r.get("created_at") or (r.get("commit") or {}).get("created_at")
                ),
                subject=(
                    r.get("message") or (r.get("commit") or {}).get("title") or ""
                ).split("\n", 1)[0]
                or None,
            )
            for r in rest.get_pages(
                f"{self._project_api(repo)}/tags?order_by=updated&sort=desc",
                self._read_headers(),
                2,
            )
        ]


def _commit(r: dict) -> CommitRow:
    return CommitRow(
        sha=r["id"],
        subject=r.get("title") or (r.get("message") or "").split("\n", 1)[0],
        author=r.get("author_name"),
        date=rest.parse_utc(r.get("authored_date") or r.get("created_at")),
    )


RC = re.compile(r"-rc\.")
