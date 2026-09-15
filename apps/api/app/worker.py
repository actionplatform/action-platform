"""`action-platform worker`: takes queued jobs from the database and runs them with the same services the API uses."""

import json
import logging
import socket
import time
import uuid
from typing import Any, Callable, Optional

from sqlalchemy import select

from action_platform.core.exception import ActionPlatformError
from action_platform.plugins import registry
from action_platform.settings import settings
from app.core.access.rules import rule_for
from app.core.auth.crypto import Sealer
from app.core.auth.secrets import Secrets
from app.core.db.database import Database
from app.core.db.models import App, Job, Organization, PluginOption, Project
from app.core.shared.urls import GitUrl
from app.repositories.source import configure_registry, get_registry
from app.schemas import (
    DeployRequest,
    PushRequest,
    ReleaseRequest,
    SyncRequest,
)
from app.services.access.enrich import enrich
from app.services.activity import ActivityService
from app.services import identity, plugins
from app.services.apps import AppService
from app.services.directory import (
    DirectoryService,
    DirectoryWrites,
)
from app.services.jobs import JobQueue
from app.services.organization_import import OrganizationImport
from app.services.workspace.lifecycle import LifecycleService

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
        self.plugins = plugins.PluginManager(self.queue, database)
        self.name = name or worker_name()
        self.handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "sync": self._sync,
            "release": self._release,
            "deploy": self._deploy,
            "push": self._push,
            "import": self._import,
            "import_github": self._import_github,
            plugins.INSTALL: self.plugins.install,
            plugins.REMOVE: self.plugins.remove,
            plugins.RESTART: self.plugins.restart,
        }
        configure_registry(database)
        registry.use_options(lambda slug: plugins.DbOptions(database, slug))

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
        organization, app, body = self._context(payload)

        return LifecycleService(
            get_registry(),
            identity=self._identity(organization, app, body),
            env=self._deploy_env(organization, app),
        ).deploy(payload["registry_id"], DeployRequest(**body))

    def _deploy_env(
        self, organization: Optional[Organization], app: Optional[App]
    ) -> dict[str, str]:
        """What the platform tells a deploy target that the repository need not: the app's `org/project/app` and every plugin option the organization set — `AP_APP`, `AP_<SLUG>_<KEY>`."""
        if organization is None or app is None:
            return {}

        with self.database.session() as db:
            project = db.get(Project, app.project_id)
            rows = db.scalars(select(PluginOption)).all()

        env = {
            "AP_APP": f"{organization.slug}/{project.slug if project else ''}/{app.name}",
        }

        for row in rows:
            value = json.loads(row.value)

            if isinstance(value, (str, int, float)) and not isinstance(value, bool):
                name = f"AP_{row.plugin}_{row.key}".upper().replace("-", "_")
                env[name] = str(value)

        return env

    def _identity(
        self, organization: Optional[Organization], app: Optional[App], body: dict
    ) -> Optional[Callable[[str], str]]:
        """What a deploy target calls for an OIDC token about this app, signed by the platform — None when the platform cannot sign."""
        if organization is None or app is None or self.sealer is None:
            return None

        with self.database.session() as db:
            project = db.get(Project, app.project_id)

        project_slug = project.slug if project else None
        subject = identity.subject_for(organization.slug, project_slug, app.name)
        issuer = identity.IdentityIssuer(
            self.database, self.sealer, settings.PUBLIC_URL
        )

        def mint(audience: str) -> str:
            return issuer.mint(
                subject,
                audience,
                organization=organization.slug,
                project=project_slug,
                app=app.name,
                stage=body.get("stage"),
            )

        return mint

    def _push(self, payload: dict[str, Any]) -> Any:
        _, _, body = self._context(payload)
        result = AppService(get_registry()).push(
            payload["registry_id"], PushRequest(**body)
        )
        self._import_after(payload)

        return result

    def _import(self, payload: dict[str, Any]) -> Any:
        return self._import_after(payload)

    def _import_github(self, payload: dict[str, Any]) -> Any:
        with self.database.session() as db:
            writes = DirectoryWrites(db, self.sealer)
            creds = writes.credentials_for(
                payload["organization_id"], payload["host_id"]
            )

            if creds is None:
                raise ActionPlatformError("the host has no credentials any more")

            return OrganizationImport(
                writes, payload["organization_id"], get_registry()
            ).run(
                creds,
                payload["host_id"],
                payload["inviter_id"],
                payload["organization"],
                payload.get("repositories") or [],
                payload.get("teams") or [],
                payload.get("people") or [],
                payload.get("role") or "developer",
                payload.get("project_id") or None,
                {
                    int(p["number"]): p.get("project_id") or None
                    for p in payload.get("projects") or []
                },
            )

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

            return ActivityService(db).sync_all(
                payload["app_id"], creds, GitUrl(url).repo
            )
