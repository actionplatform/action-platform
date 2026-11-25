"""One job at a time per app: every job of an app works on the same clone, so a second one waits until the first lets go — across threads, workers and hosts sharing the database."""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import text

from app.core.db.database import Database

NAMESPACE = 7_788_002
log = logging.getLogger(__name__)


class AppLocks:
    def __init__(self, database: Database) -> None:
        self.database = database
        self._local: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    @contextmanager
    def hold(self, app_id: Optional[str]) -> Iterator[bool]:
        """Yield True while the app is held by this caller, False when another job already holds it; a job with no app is never held back."""
        if not app_id:
            yield True
            return

        dialect = self.database.dialect

        if dialect == "postgresql":
            with self._postgres(app_id) as held:
                yield held
        elif dialect == "mysql":
            with self._mysql(app_id) as held:
                yield held
        else:
            with self._process(app_id) as held:
                yield held

    @contextmanager
    def _postgres(self, app_id: str) -> Iterator[bool]:
        with self.database.engine.connect() as connection:
            with connection.begin():
                yield bool(
                    connection.scalar(
                        text(
                            "SELECT pg_try_advisory_xact_lock(CAST(:ns AS integer), hashtext(:key))"
                        ),
                        {"ns": NAMESPACE, "key": app_id},
                    )
                )

    @contextmanager
    def _mysql(self, app_id: str) -> Iterator[bool]:
        key = f"ap_app:{app_id}"[:64]

        with self.database.engine.connect() as connection:
            held = bool(
                connection.scalar(text("SELECT GET_LOCK(:key, 0)"), {"key": key})
            )

            try:
                yield held
            finally:
                if held:
                    try:
                        connection.scalar(
                            text("SELECT RELEASE_LOCK(:key)"), {"key": key}
                        )
                    except Exception:
                        log.warning("app lock %s not released", key, exc_info=True)
                        connection.invalidate()

    @contextmanager
    def _process(self, app_id: str) -> Iterator[bool]:
        with self._guard:
            lock = self._local.setdefault(app_id, threading.Lock())

        held = lock.acquire(blocking=False)

        try:
            yield held
        finally:
            if held:
                lock.release()
