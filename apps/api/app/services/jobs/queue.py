import json
import logging
import uuid
from datetime import timedelta
from typing import Any, Optional

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session as DbSession

from app.core.db.database import Database
from app.core.db.models import Job
from app.core.shared.clock import now

MAX_ATTEMPTS = 3
CHANNEL = "ap_jobs"
log = logging.getLogger(__name__)


def loads(raw: Optional[str]) -> dict[str, Any]:
    if not raw:
        return {}

    try:
        data = json.loads(raw)
    except ValueError:
        log.warning("corrupt job json ignored", exc_info=True)

        return {}

    return data if isinstance(data, dict) else {}


class Listener:
    """A raw psycopg connection on LISTEN; `wait(timeout)` returns True when a notification arrived, False on timeout, and reconnects on the next call after an error."""

    def __init__(self, database: Any) -> None:
        self.database = database
        self.connection: Any = None

    def _connect(self) -> Any:
        connection = self.database.engine.raw_connection()
        driver = connection.driver_connection
        driver.autocommit = True
        driver.execute(f"LISTEN {CHANNEL}")

        return connection

    def wait(self, timeout: float) -> bool:
        try:
            if self.connection is None:
                self.connection = self._connect()

            driver = self.connection.driver_connection
            generator = driver.notifies(timeout=timeout)

            for _ in generator:
                generator.close()
                return True

            return False
        except Exception:
            log.debug("listener reconnects", exc_info=True)
            self.close()

            return False

    def close(self) -> None:
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception:
                pass

            self.connection = None


STALE_AFTER = timedelta(minutes=30)
BACKOFF = timedelta(seconds=30)
LIVE = ("queued", "running")


class JobQueue:
    """Queued work in the `job` table: one row per unit, claimed by workers with `SKIP LOCKED` on Postgres and a compare-and-set elsewhere."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def enqueue(
        self,
        kind: str,
        payload: dict[str, Any],
        organization_id: Optional[str] = None,
        app_id: Optional[str] = None,
        dedupe_key: Optional[str] = None,
    ) -> Job:
        with self.database.session() as s:
            if dedupe_key:
                live = s.scalar(
                    select(Job).where(
                        Job.kind == kind,
                        Job.app_id == app_id,
                        Job.dedupe_key == dedupe_key,
                        Job.status.in_(LIVE),
                    )
                )

                if live is not None:
                    return live

                for stale in s.scalars(
                    select(Job).where(
                        Job.kind == kind,
                        Job.app_id == app_id,
                        Job.dedupe_key == dedupe_key,
                    )
                ):
                    stale.dedupe_key = None

            job = Job(
                id=str(uuid.uuid4()),
                kind=kind,
                status="queued",
                organization_id=organization_id,
                app_id=app_id,
                dedupe_key=dedupe_key,
                payload=json.dumps(payload),
                run_after=now(),
            )
            s.add(job)
            s.flush()
            self._notify(s)

            return job

    def _notify(self, s: DbSession) -> None:
        """Wake listening workers; PostgreSQL only, a no-op elsewhere, and never a reason for the enqueue to fail."""
        if self.database.dialect != "postgresql":
            return

        try:
            s.execute(text(f"NOTIFY {CHANNEL}"))
        except Exception:
            log.debug("NOTIFY %s failed", CHANNEL, exc_info=True)

    def listener(self) -> Optional["Listener"]:
        """A connection that waits for enqueues, or None where the database cannot push."""
        if self.database.dialect != "postgresql":
            return None

        return Listener(self.database)

    def get(self, id: str) -> Optional[Job]:
        with self.database.session() as s:
            return s.get(Job, id)

    def for_app(
        self,
        app_id: str,
        limit: int = 20,
        kind: Optional[str] = None,
        kinds: Optional[list[str]] = None,
        offset: int = 0,
    ) -> list[Job]:
        with self.database.session() as s:
            query = (
                select(Job)
                .where(Job.app_id == app_id)
                .order_by(Job.created_at.desc())
                .offset(offset)
                .limit(limit)
            )

            if kind:
                query = query.where(Job.kind == kind)

            if kinds:
                query = query.where(Job.kind.in_(kinds))

            return list(s.scalars(query))

    def count_for_app(
        self, app_id: str, kind: Optional[str] = None, kinds: Optional[list[str]] = None
    ) -> int:
        with self.database.session() as s:
            query = select(func.count()).select_from(Job).where(Job.app_id == app_id)

            if kind:
                query = query.where(Job.kind == kind)

            if kinds:
                query = query.where(Job.kind.in_(kinds))

            return int(s.scalar(query) or 0)

    def live_deploy(self, app_id: str, stage: str) -> Optional[Job]:
        """The deploy (or preflight) of the app still queued or running for `stage` — one at a time per environment."""
        with self.database.session() as s:
            for job in s.scalars(
                select(Job).where(
                    Job.kind == "deploy",
                    Job.app_id == app_id,
                    Job.status.in_(LIVE),
                )
            ):
                body = loads(job.payload).get("body") or {}

                if (body.get("stage") or "dev") == stage:
                    return job

            return None

    def projects_being_destroyed(self, organization_id: str) -> set[str]:
        """The projects of the organization with a `destroy_project` job still queued or running."""
        with self.database.session() as s:
            rows = s.scalars(
                select(Job).where(
                    Job.kind == "destroy_project",
                    Job.organization_id == organization_id,
                    Job.status.in_(LIVE),
                )
            )

            return {str(loads(j.payload).get("project_id") or "") for j in rows} - {""}

    def claim(self, worker: str, kinds: Optional[list[str]] = None) -> Optional[Job]:
        moment = now()

        with self.database.session() as s:
            query = (
                select(Job)
                .where(Job.status == "queued", Job.run_after <= moment)
                .order_by(Job.created_at)
                .limit(1)
            )

            if kinds:
                query = query.where(Job.kind.in_(kinds))

            if self.database.dialect == "postgresql":
                query = query.with_for_update(skip_locked=True)

            job = s.scalar(query)

            if job is None:
                return None

            taken = s.execute(
                update(Job)
                .where(Job.id == job.id, Job.status == "queued")
                .values(
                    status="running",
                    locked_at=moment,
                    locked_by=worker,
                    attempts=Job.attempts + 1,
                    updated_at=moment,
                )
            ).rowcount

            if not taken:
                return None

            s.refresh(job)

            return job

    def finish(self, id: str, result: Any) -> None:
        moment = now()

        with self.database.session() as s:
            job = s.get(Job, id)

            if job is None:
                return

            job.status = "done"
            job.result = json.dumps(result, default=str)
            job.error = None
            job.finished_at = moment
            job.updated_at = moment
            job.locked_at = None
            job.locked_by = None

    def fail(self, id: str, error: str, retry: bool = True) -> None:
        moment = now()

        with self.database.session() as s:
            job = s.get(Job, id)

            if job is None:
                return

            again = retry and job.attempts < MAX_ATTEMPTS
            job.status = "queued" if again else "failed"
            job.error = error[:4000]
            job.updated_at = moment
            job.locked_at = None
            job.locked_by = None

            if again:
                job.run_after = moment + BACKOFF * (2 ** (job.attempts - 1))
            else:
                job.finished_at = moment

    def reap(self) -> int:
        cutoff = now() - STALE_AFTER

        with self.database.session() as s:
            return s.execute(
                update(Job)
                .where(Job.status == "running", Job.locked_at < cutoff)
                .values(
                    status="queued",
                    locked_at=None,
                    locked_by=None,
                    error="worker lost",
                    updated_at=now(),
                )
            ).rowcount

    @staticmethod
    def view(job: Job) -> dict[str, Any]:
        payload = loads(job.payload)
        body = payload.get("body") if isinstance(payload.get("body"), dict) else {}

        return {
            "id": job.id,
            "kind": job.kind,
            "status": job.status,
            "app_id": job.app_id,
            "attempts": job.attempts,
            "stage": body.get("stage"),
            "dry_run": body.get("dry_run"),
            "version": body.get("version"),
            "started_at": job.locked_at,
            "user_id": payload.get("user_id") or payload.get("by"),
            "result": _result(job.result),
            "error": job.error,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "finished_at": job.finished_at,
        }


def _result(raw: Optional[str]) -> Any:
    if not raw:
        return None

    try:
        return json.loads(raw)
    except ValueError:
        return None
