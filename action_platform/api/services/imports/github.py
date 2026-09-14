"""Releases and pull requests as GitHub answers them, in the platform's shape."""

from typing import Any

from action_platform.api.services.credentials import Credentials
from action_platform.api.services.http import get_pages
from action_platform.api.services.imports.common import auth, parse_time


def releases(creds: Credentials, repo: str) -> list[dict[str, Any]]:
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
            "published_at": parse_time(r.get("published_at") or r.get("created_at")),
            "source": "github",
        }
        for r in get_pages(f"{api}/repos/{repo}/releases", auth(creds))
    ]


def pull_requests(creds: Credentials, repo: str) -> list[dict[str, Any]]:
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
            "created_at": parse_time(r["created_at"]),
            "updated_at": parse_time(r["updated_at"]),
            "merged_at": parse_time(r.get("merged_at")),
            "source": "github",
        }
        for r in get_pages(
            f"{api}/repos/{repo}/pulls?state=all&sort=updated&direction=desc",
            auth(creds),
            10,
        )
    ]
