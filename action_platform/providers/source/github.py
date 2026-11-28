"""GitHub SourceHost provider.

With a token it talks to the REST API (github.com or GitHub Enterprise via
`base_url`); without one it falls back to the `gh` CLI and whatever that is
logged in as.
"""

from __future__ import annotations

import base64
import json
import shutil
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

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


REPO_NAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*)/[A-Za-z0-9._-]+$")


class SourceGithub(SourceHost):
    """
    Import:
        from action_platform.providers import SourceGithub

    Example:
        SourceGithub(repo="owner/my-project", token="ghp_…")

    Args:
        repo (str): "owner/name".
        token (str | None): personal access or app token; None uses the gh CLI.
        base_url (str | None): API root for GitHub Enterprise, e.g. https://ghe.example.com/api/v3.
    """

    name = "github"

    def __init__(
        self, repo: str, token: str | None = None, base_url: str | None = None
    ) -> None:
        if repo and not REPO_NAME.match(repo):
            raise ProviderError(f"repository {repo!r} is not owner/name")

        self.repo = repo
        self.token = token
        self.api = (base_url or "https://api.github.com").rstrip("/")
        self.web = (
            "https://github.com"
            if self.api == "https://api.github.com"
            else self.api.removesuffix("/api/v3")
        )

    def _require_credentials(self) -> None:
        if not self.token and not shutil.which("gh"):
            raise ProviderError(
                "no GitHub credentials for this repository: on the platform, connect a GitHub host "
                "in Settings; on the CLI, set ACTION_PLATFORM_GITHUB_TOKEN or install https://cli.github.com"
            )

    def _rest(self, method: str, path: str, body: dict | None = None):
        self._require_credentials()

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
        self._require_credentials()
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
                if "not accessible by integration" in str(e):
                    raise ProviderError(
                        f"the GitHub App cannot create repositories for {owner}: install it on that "
                        "account or organization with access to all repositories, and make sure its "
                        "repository permission 'Administration' is read and write (GitHub → Settings → "
                        "Developer settings → GitHub Apps → Permissions & events)"
                    ) from e

                if "already exists" not in str(e):
                    raise

            return f"{self.web}/{repo}.git"

        if not REPO_NAME.match(repo):
            raise ProviderError(f"repository name {repo!r} is not owner/name")

        args = ["gh", "repo", "create", "--private" if private else "--public"]

        if description:
            args += ["--description", description]

        args += ["--", repo]

        result = subprocess.run(args, check=False, capture_output=True, text=True)

        if result.returncode != 0:
            raise ProviderError(f"gh repo create failed: {result.stderr.strip()}")

        return f"https://github.com/{repo}.git"

    def delete_repository(self, repo: str) -> None:
        try:
            self._rest("DELETE", f"/repos/{repo}")
        except ProviderError as e:
            if "→ 404" in str(e):
                return

            if "→ 403" in str(e):
                raise ProviderError(
                    f"the {self.name} token may not delete {repo}: reconnect the host so it asks for "
                    "the delete_repo scope, or delete the repository on GitHub"
                ) from e

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
        title = name or tag

        if self.token:
            data = self._rest(
                "POST",
                f"/repos/{self.repo}/releases",
                {
                    "tag_name": tag,
                    "name": title,
                    "body": notes,
                    "draft": draft,
                    "prerelease": prerelease,
                    "make_latest": "true" if latest and not prerelease else "false",
                },
            )

            return ReleaseRef(id=str(data["id"]), tag=tag, url=data["html_url"])

        args = ["release", "create", tag, "--title", title, "--notes", notes]

        if draft:
            args.append("--draft")

        if prerelease:
            args.append("--prerelease")

        if not latest:
            args += ["--latest=false"]

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

    def _read_headers(self) -> dict[str, str]:
        headers = {"x-github-api-version": "2022-11-28"}

        if self.token:
            headers["authorization"] = f"Bearer {self.token}"

        return headers

    def releases(self, repo: str) -> list[ReleaseRow]:
        return [
            ReleaseRow(
                tag=r["tag_name"],
                name=r.get("name"),
                body=r.get("body"),
                url=r.get("html_url"),
                author=(r.get("author") or {}).get("login"),
                sha=None,
                prerelease=bool(r.get("prerelease")),
                draft=bool(r.get("draft")),
                published_at=rest.parse_utc(
                    r.get("published_at") or r.get("created_at")
                ),
                source="github",
            )
            for r in rest.get_pages(
                f"{self.api}/repos/{repo}/releases", self._read_headers()
            )
        ]

    def pull_requests(self, repo: str) -> list[PullRequestRow]:
        return [
            PullRequestRow(
                number=r["number"],
                title=r["title"],
                url=r["html_url"],
                author=(r.get("user") or {}).get("login"),
                head=r["head"]["ref"],
                base=r["base"]["ref"],
                state="merged"
                if r.get("merged_at")
                else "open"
                if r.get("state") == "open"
                else "closed",
                draft=bool(r.get("draft")),
                created_at=rest.parse_utc(r["created_at"]),
                updated_at=rest.parse_utc(r["updated_at"]),
                merged_at=rest.parse_utc(r.get("merged_at")),
                source="github",
            )
            for r in rest.get_pages(
                f"{self.api}/repos/{repo}/pulls?state=all&sort=updated&direction=desc",
                self._read_headers(),
                10,
            )
        ]

    def commits(
        self, repo: str, ref: str, limit: int = 50, path: str | None = None
    ) -> list[CommitRow]:
        only = f"&path={quote(path)}" if path else ""
        rows = rest.call(
            "GET",
            f"{self.api}/repos/{repo}/commits?sha={quote(ref, safe='')}&per_page={max(1, min(limit, 100))}{only}",
            self._read_headers(),
        )

        return [_commit(r) for r in rows or []][:limit]

    def compare(self, repo: str, base: str, head: str) -> list[CommitRow]:
        data = rest.call(
            "GET",
            f"{self.api}/repos/{repo}/compare/{quote(base, safe='')}...{quote(head, safe='')}",
            self._read_headers(),
        )

        return [_commit(r) for r in reversed((data or {}).get("commits") or [])]

    def file(self, repo: str, ref: str, path: str) -> str | None:
        try:
            data = rest.call(
                "GET",
                f"{self.api}/repos/{repo}/contents/{quote(path)}?ref={quote(ref, safe='')}",
                self._read_headers(),
            )
        except rest.Missing:
            return None

        if not isinstance(data, dict) or data.get("type") != "file":
            return None

        return base64.b64decode(data.get("content") or "").decode(errors="replace")

    def tags(self, repo: str) -> list[TagRow]:
        owner, name = repo.split("/", 1)
        data = rest.call(
            "POST",
            self.graphql,
            self._read_headers(),
            {"query": TAGS_QUERY, "variables": {"owner": owner, "name": name}},
        )

        if not isinstance(data, dict) or data.get("errors"):
            raise ProviderError(
                f"GitHub could not list the tags of {repo}: {(data or {}).get('errors')}"
            )

        refs = ((data.get("data") or {}).get("repository") or {}).get("refs") or {}

        return [_tag(node) for node in refs.get("nodes") or []]

    @property
    def graphql(self) -> str:
        if self.api == "https://api.github.com":
            return "https://api.github.com/graphql"

        return f"{self.api.removesuffix('/v3')}/graphql"


TAGS_QUERY = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    refs(refPrefix: "refs/tags/", first: 100, orderBy: {field: TAG_COMMIT_DATE, direction: DESC}) {
      nodes {
        name
        target {
          __typename
          oid
          ... on Commit { committedDate message }
          ... on Tag { message tagger { date } target { oid } }
        }
      }
    }
  }
}
"""


def _tag(node: dict) -> TagRow:
    target = node.get("target") or {}

    if target.get("__typename") == "Tag":
        sha = (target.get("target") or {}).get("oid") or target.get("oid") or ""
        date = (target.get("tagger") or {}).get("date")
    else:
        sha = target.get("oid") or ""
        date = target.get("committedDate")

    return TagRow(
        name=node["name"],
        sha=sha,
        date=rest.parse_utc(date),
        subject=(target.get("message") or "").split("\n", 1)[0] or None,
    )


def _commit(r: dict) -> CommitRow:
    commit = r.get("commit") or {}
    author = commit.get("author") or {}

    return CommitRow(
        sha=r["sha"],
        subject=(commit.get("message") or "").split("\n", 1)[0],
        author=author.get("name") or (r.get("author") or {}).get("login"),
        date=rest.parse_utc(author.get("date")),
    )
