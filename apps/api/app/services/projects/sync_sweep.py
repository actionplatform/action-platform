"""The scheduled sync: every minute the apps whose turn came get a `sync` job, sooner the more recently they changed."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import or_, select

from app.core.db.database import Database
from app.core.db.models import App, Job, Project
from app.core.shared.clock import now

SWEEP = "sync_sweep"
SWEEP_EVERY = timedelta(minutes=1)
BATCH = 200
INTERVALS = (
    (timedelta(hours=1), timedelta(minutes=2)),
    (timedelta(days=1), timedelta(minutes=10)),
    (timedelta(days=7), timedelta(hours=1)),
)
COLD = timedelta(hours=6)
NEVER = timedelta(hours=1)


def interval(last_change: Optional[datetime], at: datetime) -> timedelta:
    if last_change is None:
        return NEVER

    age = at - last_change

    return next((every for within, every in INTERVALS if age < within), COLD)


class SyncSweep:
    def __init__(self, database: Database, queue: Any) -> None:
        self.database = database
        self.queue = queue

    def schedule(self, after: timedelta = SWEEP_EVERY) -> None:
        """Queue the next sweep unless one is already waiting."""
        with self.database.session() as s:
            waiting = s.scalar(
                select(Job.id).where(Job.kind == SWEEP, Job.status == "queued")
            )

        if waiting is None:
            self.queue.enqueue(SWEEP, {}, run_after=now() + after)

    def run(self) -> dict[str, int]:
        self.schedule()
        at = now()

        with self.database.session() as s:
            due = s.execute(
                select(App, Project.organization_id)
                .join(Project, Project.id == App.project_id)
                .where(or_(App.next_sync_at.is_(None), App.next_sync_at <= at))
                .order_by(App.next_sync_at.is_not(None), App.next_sync_at)
                .limit(BATCH)
            ).all()
            wanted = []

            for app, organization_id in due:
                every = interval(app.last_change_at, at)
                app.next_sync_at = at + every + every * random.uniform(0, 0.1)
                wanted.append((app.id, app.registry_id, organization_id))

            s.commit()

        for app_id, registry_id, organization_id in wanted:
            self.queue.enqueue(
                "sync",
                sync_payload(organization_id, app_id, registry_id),
                organization_id=organization_id,
                app_id=app_id,
                dedupe_key="sync",
            )

        return {"apps": len(wanted)}

    def changed(self, app_id: str) -> None:
        """The app just changed: sync it soon again."""
        at = now()

        with self.database.session() as s:
            app = s.get(App, app_id)

            if app is not None:
                app.last_change_at = at
                app.next_sync_at = at + interval(at, at)
                s.commit()


def sync_payload(organization_id: str, app_id: str, registry_id: str) -> dict[str, Any]:
    return {
        "path": f"apps/{registry_id}/sync",
        "method": "POST",
        "body": {},
        "registry_id": registry_id,
        "organization_id": organization_id,
        "app_id": app_id,
        "user_id": None,
        "scheduled": True,
    }
