"""GitLab SourceHost provider over the REST API v4 (gitlab.com or self-hosted via `base_url`)."""

from __future__ import annotations

import urllib.parse
from pathlib import Path

from action_platform.abc.source_host import SourceHost
from action_platform.core.context import Context, PRRef, ReleaseRef
from action_platform.core.exception import ProviderError
from action_platform.providers.source import rest
from action_platform.settings import settings


class SourceGitlab(SourceHost):
    """
    Args:
        repo (str): "group/name" (subgroups allowed: "group/sub/name").
        token (str | None): personal / project / group access token; default from ACTION_PLATFORM_GITLAB_TOKEN / GITLAB_TOKEN.
        base_url (str | None): instance root, e.g. https://gitlab.example.com (default https://gitlab.com).
    """

    name = "gitlab"

    def __init__(
        self, repo: str, token: str | None = None, base_url: str | None = None
    ) -> None:
        self.repo = repo
        self.token = token or settings.GITLAB_TOKEN
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
    ) -> ReleaseRef:
        if prerelease:
            notes = f"_Pre-release_\n\n{notes}"

        data = self._rest(
            "POST",
            f"/projects/{self._id}/releases",
            {"tag_name": tag, "name": tag, "description": notes},
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
