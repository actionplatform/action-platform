"""`action-platform-api worker`: takes queued jobs from the database and hands each to the handler its context registered — the same services the API uses."""

import json
import logging
import socket
import time
import uuid
from typing import Optional

from action_platform.core.exception import ActionPlatformError
from action_platform.plugins import registry as plugin_registry
from app.core.auth.crypto import Sealer
from app.core.auth.secrets import Secrets
from app.core.db.database import Database
from app.core.db.models import Job
from app.repositories.registry import Registry
from app.repositories.source import configure_registry, get_registry
from app.services.integrations import plugins
from app.services.jobs import JobQueue, handlers as _handlers  # noqa: F401 — registers the job kinds
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
        self.plugins = plugins.PluginManager(self.queue, database)
        self.name = name or worker_name()

        if registry is None:
            configure_registry(database)
            registry = get_registry()

        self.registry = registry
        self.handlers = handlers(
            JobServices(database, self.sealer, registry, self.plugins)
        )
        plugin_registry.use_options(lambda slug: plugins.DbOptions(database, slug))

    def run(self, interval: float = 2.0, once: bool = False) -> int:
        done = 0

        while True:
            self.queue.reap()
            job = self.queue.claim(self.name, list(self.handlers))

            if job is None:
                if once:
                    return done

                time.sleep(interval)
                continue

            self.handle(job)
            done += 1

    def handle(self, job: Job) -> None:
        payload = json.loads(job.payload or "{}")
        handler = self.handlers.get(job.kind)

        if handler is None:
            self.queue.fail(job.id, f"no handler for {job.kind}", retry=False)

            return

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

        self.queue.finish(job.id, result)
        log.info("job %s %s done", job.kind, job.id)
