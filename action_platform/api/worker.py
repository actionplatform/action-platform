"""`action-platform worker`: takes queued jobs from the database and runs them with the same services the API uses."""

import json
import logging
import socket
import time
import uuid
from typing import Any, Callable, Optional

from action_platform.api.access.enrich import enrich
from action_platform.api.access.gate import repo_from_url
from action_platform.api.access.rules import rule_for
from action_platform.api.auth.crypto import Sealer
from action_platform.api.auth.secrets import Secrets
from action_platform.api.core.deps import configure_registry, get_registry
from action_platform.api.db.database import Database
from action_platform.api.db.models import App, Job, Organization
from action_platform.api.schemas import (
    DeployRequest,
    PushRequest,
    ReleaseRequest,
    SyncRequest,
)
from action_platform.api.services.apps import AppService
from action_platform.api.services.directory import DirectoryService
from action_platform.api.services.imports import ImportService
from action_platform.api.services.jobs import JobQueue
from action_platform.api.services.lifecycle import LifecycleService
from action_platform.core.exception import ActionPlatformError

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
        self, database: Database, secrets: Optional[Secrets], name: Optional[str] = None
    ) -> None:
        self.database = database
        self.secrets = secrets
        self.sealer = Sealer(secrets) if secrets else None
        self.queue = JobQueue(database)
        self.name = name or worker_name()
        self.handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "sync": self._sync,
            "release": self._release,
            "deploy": self._deploy,
            "push": self._push,
            "import": self._import,
        }
        configure_registry(database)

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

    def _context(
        self, payload: dict[str, Any]
    ) -> tuple[Optional[Organization], Optional[App], dict[str, Any]]:
        with self.database.session() as db:
            directory = DirectoryService(db, self.sealer)
            organization = (
                db.get(Organization, payload["organization_id"])
                if payload.get("organization_id")
                else None
            )
            app = db.get(App, payload["app_id"]) if payload.get("app_id") else None
            rule = rule_for(payload.get("method", "POST"), payload["path"])
            body = dict(payload.get("body") or {})

            if rule is not None:
                body = enrich(directory, organization, app, payload["path"], body, rule)

            if app is not None:
                directory.mark_synced(app)

            return organization, app, body

    def _sync(self, payload: dict[str, Any]) -> Any:
        _, app, body = self._context(payload)
        request = SyncRequest(**body)
        result = AppService(get_registry()).sync(
            payload["registry_id"], request.credentials, reset=request.reset
        )
        self._import_after(payload)

        return result

    def _release(self, payload: dict[str, Any]) -> Any:
        _, _, body = self._context(payload)
        result = LifecycleService(get_registry()).release(
            payload["registry_id"], ReleaseRequest(**body)
        )
        self._import_after(payload)

        return result

    def _deploy(self, payload: dict[str, Any]) -> Any:
        _, _, body = self._context(payload)

        return LifecycleService(get_registry()).deploy(
            payload["registry_id"], DeployRequest(**body)
        )

    def _push(self, payload: dict[str, Any]) -> Any:
        _, _, body = self._context(payload)
        result = AppService(get_registry()).push(
            payload["registry_id"], PushRequest(**body)
        )
        self._import_after(payload)

        return result

    def _import(self, payload: dict[str, Any]) -> Any:
        return self._import_after(payload)

    def _import_after(self, payload: dict[str, Any]) -> dict[str, Optional[str]]:
        if not payload.get("app_id") or not payload.get("organization_id"):
            return {}

        try:
            url = get_registry().get(payload["registry_id"]).url
        except ActionPlatformError:
            url = ""

        with self.database.session() as db:
            directory = DirectoryService(db, self.sealer)
            creds = directory.credentials_for(
                payload["organization_id"],
                db.get(App, payload["app_id"]).source_host_id,
            )

            return ImportService(db).sync_all(
                payload["app_id"], creds, repo_from_url(url)
            )
