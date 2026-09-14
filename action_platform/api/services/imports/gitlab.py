"""Releases and pull requests as Gitlab answers them, in the platform's shape."""

from typing import Any
from urllib.parse import quote

from action_platform.api.services.credentials import Credentials
from action_platform.api.services.http import get_pages
from action_platform.api.services.imports.common import RC, auth, parse_time


def releases(creds: Credentials, repo: str) -> list[dict[str, Any]]:
    base = (creds.base_url or "").rstrip("/") or "https://gitlab.com"

    return [
        {
            "tag": r["tag_name"],
            "name": r.get("name"),
            "body": r.get("description"),
            "url": ((r.get("_links") or {}).get("self"))
            or f"{base}/{repo}/-/releases/{r['tag_name']}",
            "author": (r.get("author") or {}).get("username"),
            "sha": ((r.get("commit") or {}).get("id") or "")[:7] or None,
            "prerelease": bool(r.get("upcoming_release"))
            or bool(RC.search(r["tag_name"])),
            "draft": False,
            "published_at": parse_time(r.get("released_at") or r.get("created_at")),
            "source": "gitlab",
        }
        for r in get_pages(
            f"{base}/api/v4/projects/{quote(repo, safe='')}/releases", auth(creds)
        )
    ]


def pull_requests(creds: Credentials, repo: str) -> list[dict[str, Any]]:
    base = (creds.base_url or "").rstrip("/") or "https://gitlab.com"

    return [
        {
            "number": r["iid"],
            "title": r["title"],
            "url": r["web_url"],
            "author": (r.get("author") or {}).get("username"),
            "head": r["source_branch"],
            "base": r["target_branch"],
            "state": "merged"
            if r.get("state") == "merged"
            else "open"
            if r.get("state") == "opened"
            else "closed",
            "draft": bool(r.get("draft")),
            "created_at": parse_time(r["created_at"]),
            "updated_at": parse_time(r["updated_at"]),
            "merged_at": parse_time(r.get("merged_at")),
            "source": "gitlab",
        }
        for r in get_pages(
            f"{base}/api/v4/projects/{quote(repo, safe='')}/merge_requests?state=all&order_by=updated_at",
            auth(creds),
            10,
        )
    ]
