"""Readiness rows: one per release and stage, rewritten every time the worker checks again."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from action_platform.core.context import Check
from app.core.db.models import Release, ReleaseReadiness
from app.core.shared.clock import now


class ReadinessStore:
    def __init__(self, db: DbSession) -> None:
        self.db = db

    def get(self, release_id: str, stage: str) -> Optional[ReleaseReadiness]:
        return self.db.scalar(
            select(ReleaseReadiness).where(
                ReleaseReadiness.release_id == release_id,
                ReleaseReadiness.stage == stage,
            )
        )

    def for_release(self, release_id: str) -> list[ReleaseReadiness]:
        rows = {
            r.stage: r
            for r in self.db.scalars(
                select(ReleaseReadiness).where(
                    ReleaseReadiness.release_id == release_id
                )
            )
        }

        return [rows[s] for s in sorted(rows)]

    def queued(
        self, release: Release, stage: str, job_id: Optional[str]
    ) -> ReleaseReadiness:
        row = self.get(release.id, stage)

        if row is None:
            row = ReleaseReadiness(
                id=str(uuid.uuid4()), release_id=release.id, stage=stage
            )
            self.db.add(row)

        row.status = "queued"
        row.job_id = job_id
        row.updated_at = now()
        self.db.flush()

        return row

    def running(self, release_id: str, stage: str) -> None:
        row = self.get(release_id, stage)

        if row is not None:
            row.status = "running"
            row.updated_at = now()

    def done(
        self,
        release: Release,
        stage: str,
        checks: Iterable[Check],
        job_id: Optional[str],
    ) -> ReleaseReadiness:
        found = list(checks)
        row = self.get(release.id, stage)

        if row is None:
            row = ReleaseReadiness(
                id=str(uuid.uuid4()), release_id=release.id, stage=stage
            )
            self.db.add(row)

        row.status = "done"
        row.ok = not any(c.blocking for c in found)
        row.checks = json.dumps([asdict(c) for c in found])
        row.job_id = job_id or row.job_id
        row.checked_at = now()
        row.updated_at = row.checked_at
        self.db.flush()

        return row

    def failed(
        self, release: Release, stage: str, error: str, job_id: Optional[str]
    ) -> ReleaseReadiness:
        return self.done(
            release,
            stage,
            [
                Check(
                    "readiness.run",
                    False,
                    error[:2000],
                    level="static",
                    fix="re-check once the cause is gone",
                )
            ],
            job_id,
        )

    def summary(self, release_ids: list[str]) -> dict[str, dict[str, str]]:
        """{release_id: {stage: "ok" | "blocked" | "pending"}} for every row of the given releases."""
        if not release_ids:
            return {}

        out: dict[str, dict[str, str]] = {}

        for row in self.db.scalars(
            select(ReleaseReadiness).where(ReleaseReadiness.release_id.in_(release_ids))
        ):
            out.setdefault(row.release_id, {})[row.stage] = verdict(row)

        return out

    @staticmethod
    def checks_of(row: ReleaseReadiness) -> list[dict[str, Any]]:
        try:
            return list(json.loads(row.checks or "[]"))
        except ValueError:
            return []


def verdict(row: ReleaseReadiness) -> str:
    if row.status != "done" or row.ok is None:
        return "pending"

    return "ok" if row.ok else "blocked"
