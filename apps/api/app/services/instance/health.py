"""Whether the instance can do its job: database, migrations, workers, and what is waiting in the queue."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text

from action_platform.settings import settings
from app.core.db.database import Database
from app.core.shared.clock import now
from app.core.shared.mail import SmtpConfig
from app.services.auth.google import callback_url
from app.services.jobs import JobQueue
from app.services.jobs.workers import GROUPS, Workers, group_of, split


class InstanceHealth:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.queue = JobQueue(database)
        self.workers = Workers(database)

    def probe(self) -> dict[str, Any]:
        """The status every caller may see: database reachable, migrations at head, a live worker per group."""
        reachable = self._reachable()
        current = reachable and self._current()
        groups = self.workers.groups() if current else {g: False for g in GROUPS}
        ok = reachable and current and all(groups.values())

        return {
            "status": "ok" if ok else "unavailable",
            "database": reachable,
            "migrations": current,
            "workers": groups,
        }

    def detail(self) -> dict[str, Any]:
        """Everything an owner needs to find out why: each worker, the queue per kind, the versions."""
        moment = now()
        rows = self.workers.all()
        live = {
            kind
            for row in rows
            if Workers.alive(row, moment)
            for kind in split(row.kinds)
        }
        depth = self.queue.depth()
        kinds = sorted(set(depth) | live)

        return {
            "workers_seen": [
                {
                    "name": row.name,
                    "host": row.host,
                    "kinds": split(row.kinds),
                    "started_at": row.started_at,
                    "last_seen": row.last_seen,
                    "alive": Workers.alive(row, moment),
                }
                for row in rows
            ],
            "queue": [
                {
                    "kind": kind,
                    "group": group_of(kind),
                    "queued": depth.get(kind, {}).get("queued", 0),
                    "running": depth.get(kind, {}).get("running", 0),
                    "oldest_queued_seconds": _age(
                        depth.get(kind, {}).get("oldest_queued"), moment
                    ),
                    "worker_running": kind in live,
                }
                for kind in kinds
            ],
        }

    @staticmethod
    def smtp(mailer: Any) -> dict[str, Any]:
        config = getattr(mailer, "config", None)

        if not isinstance(config, SmtpConfig):
            return {"configured": mailer is not None}

        return {
            "configured": True,
            "host": config.host,
            "port": config.port,
            "security": config.security,
            "sender": config.sender,
        }

    @staticmethod
    def google(configured: bool, public_url: str) -> dict[str, Any]:
        return {"configured": configured, "redirect_uri": callback_url(public_url)}

    @staticmethod
    def sentry() -> bool:
        return bool(settings.observability.dsn)

    def _reachable(self) -> bool:
        try:
            with self.database.engine.connect() as connection:
                connection.execute(text("SELECT 1"))

            return True
        except Exception:
            return False

    def _current(self) -> bool:
        try:
            return not self.database.behind()
        except Exception:
            return False


def _age(since: Optional[datetime], moment: datetime) -> Optional[int]:
    return None if since is None else max(0, int((moment - since).total_seconds()))
