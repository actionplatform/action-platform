"""Worker heartbeats: which workers are alive and what kinds they take."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete, select

from app.core.db.database import Database
from app.core.db.models import Worker
from app.core.shared.clock import now

BEAT_EVERY = 15.0
LIVE_WITHIN = timedelta(seconds=60)
FORGET_AFTER = timedelta(days=1)
NO_WORKER_AFTER = timedelta(minutes=2)
DEPLOY_KINDS = (
    "deploy",
    "readiness",
    "destroy",
    "destroy_project",
    "destroy_organization",
)
GROUPS = ("light", "deploy")


def group_of(kind: str) -> str:
    return "deploy" if kind in DEPLOY_KINDS else "light"


def split(kinds: str) -> list[str]:
    return [k for k in (kinds or "").split(",") if k]


class Workers:
    def __init__(self, database: Database) -> None:
        self.database = database

    def beat(
        self,
        name: str,
        kinds: list[str],
        host: str,
        started_at: Optional[datetime] = None,
    ) -> None:
        moment = now()

        with self.database.session() as s:
            row = s.get(Worker, name)

            if row is None:
                s.add(
                    Worker(
                        name=name,
                        kinds=",".join(kinds),
                        host=host,
                        started_at=started_at or moment,
                        last_seen=moment,
                    )
                )

                return

            row.kinds = ",".join(kinds)
            row.host = host
            row.last_seen = moment

            if started_at is not None:
                row.started_at = started_at

    def forget_old(self) -> int:
        with self.database.session() as s:
            return s.execute(
                delete(Worker).where(Worker.last_seen < now() - FORGET_AFTER)
            ).rowcount

    def all(self) -> list[Worker]:
        with self.database.session() as s:
            return list(s.scalars(select(Worker).order_by(Worker.name)))

    def get(self, name: str) -> Optional[Worker]:
        with self.database.session() as s:
            return s.get(Worker, name)

    @staticmethod
    def alive(row: Worker, moment: Optional[datetime] = None) -> bool:
        return row.last_seen >= (moment or now()) - LIVE_WITHIN

    def live_kinds(self) -> set[str]:
        moment = now()

        return {
            kind
            for row in self.all()
            if self.alive(row, moment)
            for kind in split(row.kinds)
        }

    def groups(self) -> dict[str, bool]:
        live = self.live_kinds()

        return {g: any(group_of(k) == g for k in live) for g in GROUPS}


def lacks_worker(
    status: str, kind: str, run_after: datetime, live: set[str], moment: datetime
) -> bool:
    """Queued, overdue, and no live worker takes its kind."""
    return (
        status == "queued"
        and kind not in live
        and run_after <= moment - NO_WORKER_AFTER
    )
