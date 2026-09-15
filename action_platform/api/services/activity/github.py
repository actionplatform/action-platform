"""Releases and pull requests as GitHub answers them, in the platform's shape."""

from typing import Any

from action_platform.api.abc import ImportSource
from action_platform.api.services.shared.credentials import Credentials
from action_platform.api.services.shared.http import http
from action_platform.api.services.shared.clock import parse_utc


class GithubActivity(ImportSource):
    kind = "github"

    def headers(self, creds: Credentials) -> dict[str, str]:
        return {
            "authorization": f"Bearer {creds.token}",
            "x-github-api-version": "2022-11-28",
        }

    def releases(self, creds: Credentials, repo: str) -> list[dict[str, Any]]:
        api = (creds.base_url or "").rstrip("/") or "https://api.github.com"

        return [
            {
                "tag": r["tag_name"],
                "name": r.get("name"),
                "body": r.get("body"),
                "url": r.get("html_url"),
                "author": (r.get("author") or {}).get("login"),
                "sha": None,
                "prerelease": bool(r.get("prerelease")),
                "draft": bool(r.get("draft")),
                "published_at": parse_utc(r.get("published_at") or r.get("created_at")),
                "source": "github",
            }
            for r in http.get_pages(f"{api}/repos/{repo}/releases", self.headers(creds))
        ]

    def pull_requests(self, creds: Credentials, repo: str) -> list[dict[str, Any]]:
        api = (creds.base_url or "").rstrip("/") or "https://api.github.com"

        return [
            {
                "number": r["number"],
                "title": r["title"],
                "url": r["html_url"],
                "author": (r.get("user") or {}).get("login"),
                "head": r["head"]["ref"],
                "base": r["base"]["ref"],
                "state": "merged"
                if r.get("merged_at")
                else "open"
                if r.get("state") == "open"
                else "closed",
                "draft": bool(r.get("draft")),
                "created_at": parse_utc(r["created_at"]),
                "updated_at": parse_utc(r["updated_at"]),
                "merged_at": parse_utc(r.get("merged_at")),
                "source": "github",
            }
            for r in http.get_pages(
                f"{api}/repos/{repo}/pulls?state=all&sort=updated&direction=desc",
                self.headers(creds),
                10,
            )
        ]
