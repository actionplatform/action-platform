"""`action-platform-api worker`: takes queued jobs from the database and hands each to the handler its context registered — the same services the API uses."""

import json
import logging
import socket
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
import uuid
from typing import Optional

from action_platform.core.exception import ActionPlatformError
from action_platform.plugins import registry as plugin_registry
from app.core.auth.crypto import Sealer
from app.core.auth.secrets import Secrets
from app.core.db.database import Database
from app.core.db.models import Job
from app.repositories.workspace.registry import Registry
from app.repositories.workspace.source import configure_registry, get_registry
from app.services.integrations import plugins
from app.services.jobs import JobQueue, handlers as _handlers  # noqa: F401 — registers the job kinds
from app.services.jobs.logs import JobLogs
from app.services.jobs.registry import JobServices, handlers

log = logging.getLogger("action_platform.worker")

ASYNC_ROUTES = {
    "sync": "app.sync",
    "release": "app.release",
    "deploy": "app.release",
    "push": "app.flow",
}


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
        self.name = name or worker_name()

        if registry is None:
            configure_registry(database)
            registry = get_registry()

        self.registry = registry
        self.listener = self.queue.listener()
        self.handlers = handlers(JobServices(database, self.sealer, registry))
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

        if concurrency <= 1:
            return self._run_serial(interval, once, wanted)

        return self._run_pool(interval, once, concurrency, wanted)

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

    def handle(self, job: Job) -> None:
        payload = {**json.loads(job.payload or "{}"), "job_id": job.id}
        handler = self.handlers.get(job.kind)

        if handler is None:
            self.queue.fail(job.id, f"no handler for {job.kind}", retry=False)

            return

        with self.logs.record(job.id):
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
