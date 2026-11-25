"""`action-platform-api worker`: takes queued jobs from the database and hands each to the handler its context registered — the same services the API uses."""

import json
import logging
import os
import socket
import threading
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from action_platform.core.exception import ActionPlatformError
from action_platform.plugins import registry as plugin_registry
from action_platform.settings import settings
from app.core.auth.crypto import Sealer
from app.core.auth.secrets import Secrets
from app.core.db.database import Database
from app.core.db.models import Job
from app.core.shared.clock import now
from app.repositories.workspace.registry import Registry
from app.repositories.workspace.source import configure_registry, get_registry
from app.services.integrations import plugins
from app.services.organization import InvitationSender
from app.services.jobs import JobQueue, handlers as _handlers  # noqa: F401 — registers the job kinds
from app.services.jobs.locks import AppLocks
from app.services.jobs.logs import JobLogs
from app.services.jobs.registry import JobServices, handlers
from app.services.jobs.workers import BEAT_EVERY, Workers

log = logging.getLogger("action_platform.worker")

ASYNC_ROUTES = {
    "sync": "app.sync",
    "release": "app.release",
    "deploy": "app.release",
    "push": "app.flow",
}


HEARTBEAT_SECONDS = 60.0


def worker_name() -> str:
    return f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"


class Worker:
    def __init__(
        self,
        database: Database,
        secrets: Optional[Secrets],
        name: Optional[str] = None,
        registry: Optional[Registry] = None,
    ) -> None:
        self.database = database
        self.secrets = secrets
        self.sealer = Sealer(secrets) if secrets else None
        self.queue = JobQueue(database)
        self.logs = JobLogs(database)
        self.locks = AppLocks(database)
        self.name = name or worker_name()
        self.workers = Workers(database)
        self.started_at = now()

        if registry is None:
            configure_registry(database)
            registry = get_registry()

        self.registry = registry
        self.listener = self.queue.listener()
        self.handlers = handlers(
            JobServices(
                database,
                self.sealer,
                registry,
                InvitationSender.from_env(os.environ, settings.api.public_url),
            )
        )
        plugin_registry.use_options(lambda slug: plugins.DbOptions(database, slug))

    def run(
        self,
        interval: float = 2.0,
        once: bool = False,
        concurrency: int = 1,
        kinds: Optional[list[str]] = None,
    ) -> int:
        """Claim and run jobs until the queue is empty (`once`) or forever; `concurrency` jobs at a time, each on its own thread, `kinds` to take only some."""
        wanted = [k for k in (kinds or list(self.handlers)) if k in self.handlers]

        with self.beating(wanted):
            if concurrency <= 1:
                return self._run_serial(interval, once, wanted)

            return self._run_pool(interval, once, concurrency, wanted)

    def beat(self, kinds: list[str]) -> None:
        try:
            self.workers.beat(self.name, kinds, socket.gethostname(), self.started_at)
        except Exception:
            log.warning("worker heartbeat failed", exc_info=True)

    @contextmanager
    def beating(self, kinds: list[str]) -> Iterator[None]:
        """Heartbeat in the background while the loop runs."""
        stop = threading.Event()
        self.beat(kinds)

        try:
            self.workers.forget_old()
        except Exception:
            log.debug("old workers not forgotten", exc_info=True)

        def run() -> None:
            while not stop.wait(BEAT_EVERY):
                self.beat(kinds)

        thread = threading.Thread(target=run, name=f"{self.name}:alive", daemon=True)
        thread.start()

        try:
            yield
        finally:
            stop.set()
            thread.join(timeout=5)

    def _idle(self, interval: float) -> None:
        """Sleep until something is enqueued or `interval` passes — whichever the database allows."""
        if self.listener is None or not self.listener.wait(interval):
            if self.listener is None:
                time.sleep(interval)

    def _run_serial(self, interval: float, once: bool, kinds: list[str]) -> int:
        done = 0

        while True:
            self.queue.reap()
            job = self.queue.claim(self.name, kinds)

            if job is None:
                if once:
                    return done

                self._idle(interval)
                continue

            self.handle(job)
            done += 1

    def _run_pool(
        self, interval: float, once: bool, concurrency: int, kinds: list[str]
    ) -> int:
        done = 0
        live: set[Future] = set()

        with ThreadPoolExecutor(
            max_workers=concurrency, thread_name_prefix=self.name
        ) as pool:
            while True:
                live = {f for f in live if not f.done()}
                self.queue.reap()
                job = (
                    self.queue.claim(self.name, kinds)
                    if len(live) < concurrency
                    else None
                )

                if job is None:
                    if once and not live:
                        return done

                    if once:
                        wait(live, return_when=FIRST_COMPLETED)
                        continue

                    self._idle(interval if not live else min(interval, 0.5))
                    continue

                live.add(pool.submit(self.handle, job))
                done += 1

    @contextmanager
    def holding(self, id: str) -> Iterator[None]:
        """Keep job `id`'s lock fresh while it runs, so a deploy that follows a long pipeline is not handed to another worker as lost."""
        stop = threading.Event()

        def beat() -> None:
            while not stop.wait(HEARTBEAT_SECONDS):
                try:
                    self.queue.touch(id, self.name)
                except Exception:
                    log.warning("job %s: lock refresh failed", id, exc_info=True)

        thread = threading.Thread(target=beat, name=f"{self.name}:beat", daemon=True)
        thread.start()

        try:
            yield
        finally:
            stop.set()
            thread.join(timeout=5)

    def handle(self, job: Job) -> None:
        handler = self.handlers.get(job.kind)

        if handler is None:
            self.queue.fail(job.id, f"no handler for {job.kind}", retry=False)

            return

        with self.locks.hold(job.app_id) as held:
            if not held:
                log.info("job %s %s waits: its app is busy", job.kind, job.id)
                self.queue.defer(job.id, self.name)

                return

            self._run(job, handler)

    def _run(self, job: Job, handler: Any) -> None:
        payload = {
            **json.loads(job.payload or "{}"),
            "job_id": job.id,
            "attempt": job.attempts,
        }

        with self.logs.record(job.id), self.holding(job.id):
            log.info("job %s %s starts (attempt %s)", job.kind, job.id, job.attempts)

            try:
                result = handler(payload)
            except ActionPlatformError as e:
                log.warning("job %s %s refused: %s", job.kind, job.id, e)
                self.queue.fail(job.id, str(e), retry=False)

                return
            except Exception as e:
                log.exception("job %s %s failed", job.kind, job.id)
                self.queue.fail(job.id, f"{type(e).__name__}: {e}")

                return

            log.info("job %s %s done", job.kind, job.id)

        self.queue.finish(job.id, result)
