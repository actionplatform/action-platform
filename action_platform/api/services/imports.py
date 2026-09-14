import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from action_platform.api.db.models import PullRequest, Release
from action_platform.api.services.directory import Credentials
from action_platform.api.services.http import basic, get_pages, get_values
from action_platform.core.exception import ProviderError

RC = re.compile(r"-rc\.")


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (
        parsed.astimezone(timezone.utc).replace(tzinfo=None)
        if parsed.tzinfo
        else parsed
    )


def _auth(creds: Credentials) -> dict[str, str]:
    if creds.kind == "github":
        return {
            "authorization": f"Bearer {creds.token}",
            "x-github-api-version": "2022-11-28",
        }
    if creds.kind == "bitbucket" and creds.username:
        return {"authorization": basic(creds.username, creds.token)}
    return {"authorization": f"Bearer {creds.token}"}


def remote_releases(creds: Credentials, repo: str) -> list[dict[str, Any]]:
    if creds.kind == "github":
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
                "published_at": parse_time(
                    r.get("published_at") or r.get("created_at")
                ),
                "source": "github",
            }
            for r in get_pages(f"{api}/repos/{repo}/releases", _auth(creds))
        ]
    if creds.kind == "gitlab":
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
                f"{base}/api/v4/projects/{quote(repo, safe='')}/releases", _auth(creds)
            )
        ]
    if creds.kind == "bitbucket":
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
                "published_at": parse_time((r.get("target") or {}).get("date")),
                "source": "bitbucket",
            }
            for r in get_values(
                f"https://api.bitbucket.org/2.0/repositories/{repo}/refs/tags?sort=-target.date&pagelen=100",
                _auth(creds),
            )
        ]
    return []


def remote_pull_requests(creds: Credentials, repo: str) -> list[dict[str, Any]]:
    if creds.kind == "github":
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
                _auth(creds),
                10,
            )
        ]
    if creds.kind == "gitlab":
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
                _auth(creds),
                10,
            )
        ]
    if creds.kind == "bitbucket":
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
                "created_at": parse_time(r["created_on"]),
                "updated_at": parse_time(r["updated_on"]),
                "merged_at": parse_time(r["updated_on"])
                if r.get("state") == "MERGED"
                else None,
                "source": "bitbucket",
            }
            for r in get_values(
                f"https://api.bitbucket.org/2.0/repositories/{repo}/pullrequests?state=OPEN&state=MERGED&state=DECLINED&sort=-updated_on&pagelen=50",
                _auth(creds),
            )
        ]
    return []


class ImportService:
    """Releases and pull requests copied from the source host into the database, so pages and agents read them without touching the provider."""

    def __init__(self, db: DbSession) -> None:
        self.db = db

    def sync_releases(
        self, app_id: str, creds: Optional[Credentials], repo: Optional[str]
    ) -> int:
        if creds is None or not repo:
            raise ProviderError("no source host")
        remote = remote_releases(creds, repo)
        by_tag = {
            r.tag: r
            for r in self.db.scalars(select(Release).where(Release.app_id == app_id))
        }
        moment = now()
        for item in remote:
            row = by_tag.get(item["tag"])
            if row is None:
                row = Release(id=str(uuid.uuid4()), app_id=app_id)
                self.db.add(row)
            for key, value in item.items():
                setattr(row, key, value)
            row.synced_at = moment
        self.db.flush()
        return len(remote)

    def sync_pull_requests(
        self, app_id: str, creds: Optional[Credentials], repo: Optional[str]
    ) -> int:
        if creds is None or not repo:
            raise ProviderError("no source host")
        remote = remote_pull_requests(creds, repo)
        by_number = {
            r.number: r
            for r in self.db.scalars(
                select(PullRequest).where(PullRequest.app_id == app_id)
            )
        }
        for item in remote:
            row = by_number.get(item["number"])
            if row is None:
                row = PullRequest(id=str(uuid.uuid4()), app_id=app_id)
                self.db.add(row)
            for key, value in item.items():
                setattr(row, key, value)
        self.db.flush()
        return len(remote)

    def sync_all(
        self, app_id: str, creds: Optional[Credentials], repo: Optional[str]
    ) -> dict[str, Optional[str]]:
        errors: dict[str, Optional[str]] = {}
        for name, fn in (
            ("releases", self.sync_releases),
            ("pull_requests", self.sync_pull_requests),
        ):
            try:
                fn(app_id, creds, repo)
                errors[name] = None
            except ProviderError as e:
                errors[name] = str(e)
        return errors
