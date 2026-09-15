"""Releases and pull requests as Bitbucket answers them, in the platform's shape."""

import re
from typing import Any

from action_platform_api.core.abc import ImportSource
from action_platform_api.core.shared.credentials import Credentials
from action_platform_api.core.shared.http import BasicAuth, http
from action_platform_api.core.shared.clock import parse_utc

RC = re.compile(r"-rc\.")


class BitbucketActivity(ImportSource):
    kind = "bitbucket"

    def headers(self, creds: Credentials) -> dict[str, str]:
        if creds.username:
            return {"authorization": BasicAuth.header(creds.username, creds.token)}

        return {"authorization": f"Bearer {creds.token}"}

    def releases(self, creds: Credentials, repo: str) -> list[dict[str, Any]]:
        return [
            {
                "tag": r["name"],
                "name": r["name"],
                "body": r.get("message"),
                "url": ((r.get("links") or {}).get("html") or {}).get("href")
                or f"https://bitbucket.org/{repo}/src/{r['name']}/",
                "author": (
                    ((r.get("target") or {}).get("author") or {}).get("user") or {}
                ).get("display_name"),
                "sha": ((r.get("target") or {}).get("hash") or "")[:7] or None,
                "prerelease": bool(RC.search(r["name"])),
                "draft": False,
                "published_at": parse_utc((r.get("target") or {}).get("date")),
                "source": "bitbucket",
            }
            for r in http.get_values(
                f"https://api.bitbucket.org/2.0/repositories/{repo}/refs/tags?sort=-target.date&pagelen=100",
                self.headers(creds),
            )
        ]

    def pull_requests(self, creds: Credentials, repo: str) -> list[dict[str, Any]]:
        return [
            {
                "number": r["id"],
                "title": r["title"],
                "url": ((r.get("links") or {}).get("html") or {}).get("href")
                or f"https://bitbucket.org/{repo}/pull-requests/{r['id']}",
                "author": (r.get("author") or {}).get("display_name"),
                "head": r["source"]["branch"]["name"],
                "base": r["destination"]["branch"]["name"],
                "state": "merged"
                if r.get("state") == "MERGED"
                else "open"
                if r.get("state") == "OPEN"
                else "closed",
                "draft": False,
                "created_at": parse_utc(r["created_on"]),
                "updated_at": parse_utc(r["updated_on"]),
                "merged_at": parse_utc(r["updated_on"])
                if r.get("state") == "MERGED"
                else None,
                "source": "bitbucket",
            }
            for r in http.get_values(
                f"https://api.bitbucket.org/2.0/repositories/{repo}/pullrequests?state=OPEN&state=MERGED&state=DECLINED&sort=-updated_on&pagelen=50",
                self.headers(creds),
            )
        ]
