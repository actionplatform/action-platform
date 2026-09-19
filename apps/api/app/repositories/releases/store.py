"""The platform's releases: one row per tag of an app, whatever named it first — a release cut here, the code host, a tag seen in the clone."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from action_platform.core.scopes import shape_of
from app.core.db.models import Release
from app.core.shared.clock import now

TAG = re.compile(r"^(?:(?P<component>[A-Za-z0-9_.-]+)/)?v?(?P<version>\d.*)$")

HOST_FIELDS = ("name", "body", "url", "author", "prerelease", "draft", "published_at")


def split_tag(tag: str) -> tuple[str, str]:
    """(component, version) of a tag: `v1.2.3` → ("", "1.2.3"), `web/v1.2.3` → ("web", "1.2.3")."""
    found = TAG.match(tag.strip())

    if found is None:
        return "", tag.strip()

    return found.group("component") or "", found.group("version")


def tag_of(component: str, version: str) -> str:
    return f"{component}/v{version}" if component else f"v{version}"


class ReleaseStore:
    def __init__(self, db: DbSession) -> None:
        self.db = db

    def get(self, app_id: str, tag: str) -> Optional[Release]:
        return self.db.scalar(
            select(Release).where(Release.app_id == app_id, Release.tag == tag)
        )

    def ensure(
        self,
        app_id: str,
        tag: str,
        source: str,
        sha: Optional[str] = None,
        **fields: Any,
    ) -> Release:
        """The row for `tag`, created when missing. A host or the platform overrides what git alone knew; git never overrides a host."""
        row = self.get(app_id, tag)
        component, version = split_tag(tag)
        shape = fields.pop("shape", None)

        if row is None:
            row = Release(
                id=str(uuid.uuid4()),
                app_id=app_id,
                tag=tag,
                component=component,
                version=version,
                source=source,
                prerelease="-" in version,
                draft=False,
                shape=shape or shape_of(version),
            )
            self.db.add(row)

        row.component = component
        row.version = version

        if shape:
            row.shape = shape

        if sha and (not row.sha or source != "git"):
            row.sha = sha

        if source != "git" or row.source == "git":
            row.source = source if source != "git" else row.source

            for key, value in fields.items():
                if key in HOST_FIELDS and value is not None:
                    setattr(row, key, value)

        row.synced_at = now()
        self.db.flush()

        return row

    def from_tags(self, app_id: str, tags: list[dict[str, Any]]) -> int:
        """Every tag of the clone as a row — the source that catches what no host names."""
        for t in tags:
            self.ensure(
                app_id,
                t["tag"],
                "git",
                sha=t.get("sha"),
                published_at=self._date(t.get("date")),
            )

        return len(tags)

    def for_version(
        self, app_id: str, component: str, version: str, sha: Optional[str] = None
    ) -> Release:
        return self.ensure(app_id, tag_of(component, version), "git", sha=sha)

    @staticmethod
    def _date(value: Any) -> Optional[datetime]:
        if not value:
            return None

        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None
