"""What a job wrote while it ran: appended in small batches as the lines arrive, read back from any sequence number."""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from sqlalchemy import delete, func, select

from action_platform.logging import attach, capture
from app.core.db.database import Database
from app.core.db.models import Job, JobLog
from app.core.shared.clock import now

FLUSH_EVERY = 0.5
FLUSH_AT = 50
MAX_LINES = 20000
MAX_LINE = 4000
PAGE = 1000

attach("app")


class Recorder:
    """The sink of one job: thread-safe, buffered, capped."""

    def __init__(self, database: Database, job_id: str) -> None:
        self.database = database
        self.job_id = job_id
        self.buffer: list[str] = []
        self.seq = 0
        self.lock = threading.Lock()
        self.flushed_at = time.monotonic()
        self.dropped = False

    def write(self, line: str) -> None:
        with self.lock:
            if self.seq >= MAX_LINES:
                if not self.dropped:
                    self.dropped = True
                    self.buffer.append(f"… output truncated after {MAX_LINES} lines")
                    self.seq += 1
                    self._flush_locked()

                return

            self.buffer.append(line[:MAX_LINE])
            self.seq += 1
            due = time.monotonic() - self.flushed_at >= FLUSH_EVERY

            if len(self.buffer) >= FLUSH_AT or due:
                self._flush_locked()

    def flush(self) -> None:
        with self.lock:
            self._flush_locked()

    def _flush_locked(self) -> None:
        if not self.buffer:
            self.flushed_at = time.monotonic()

            return

        lines, self.buffer = self.buffer, []
        first = self.seq - len(lines)
        moment = now()

        try:
            with self.database.session() as s:
                s.add_all(
                    [
                        JobLog(job_id=self.job_id, seq=first + i, line=line, at=moment)
                        for i, line in enumerate(lines)
                    ]
                )
        except Exception:
            pass

        self.flushed_at = time.monotonic()


class JobLogs:
    def __init__(self, database: Database) -> None:
        self.database = database

    @contextmanager
    def record(self, job_id: str) -> Iterator[Recorder]:
        recorder = Recorder(self.database, job_id)
        recorder.seq = self.count(job_id)

        with capture(recorder.write):
            try:
                yield recorder
            finally:
                recorder.flush()

    def after(self, job_id: str, after: int = 0, limit: int = PAGE) -> list[JobLog]:
        limit = max(1, min(PAGE, limit))

        with self.database.session() as s:
            return list(
                s.scalars(
                    select(JobLog)
                    .where(JobLog.job_id == job_id, JobLog.seq >= after)
                    .order_by(JobLog.seq)
                    .limit(limit)
                )
            )

    def count(self, job_id: str) -> int:
        with self.database.session() as s:
            return int(
                s.scalar(
                    select(func.count())
                    .select_from(JobLog)
                    .where(JobLog.job_id == job_id)
                )
                or 0
            )

    def forget(self, job_id: str) -> None:
        with self.database.session() as s:
            s.execute(delete(JobLog).where(JobLog.job_id == job_id))

    @staticmethod
    def view(job: Optional[Job], rows: list[JobLog], after: int = 0) -> dict[str, Any]:
        finished = job is None or job.status in ("done", "failed")

        return {
            "lines": [{"seq": r.seq, "at": r.at, "line": r.line} for r in rows],
            "next": rows[-1].seq + 1 if rows else after,
            "status": job.status if job else "unknown",
            "finished": finished,
        }
