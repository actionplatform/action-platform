"""One callable per job kind, built on the same services the API uses; the worker only claims jobs and dispatches here."""

from __future__ import annotations

from typing import Any, Callable, Optional

from action_platform.core.exception import ActionPlatformError
from action_platform.settings import settings
from app.core.auth.crypto import Sealer
from app.core.db.database import Database
from app.core.db.models import App
from app.core.shared.urls import GitUrl
from app.repositories.registry import Registry
from app.schemas import DeployRequest, PushRequest, ReleaseRequest, SyncRequest
from app.services import plugins
from app.services.activity import ActivityService
from app.services.apps import AppService
from app.services.deploy import DeployEnv
from app.services.directory import DirectoryService, DirectoryWrites
from app.services.identity.signer import AppIdentity
from app.services.jobs.context import JobContext
from app.services.organization_import import OrganizationImport
from app.services.workspace.lifecycle import LifecycleService

Handler = Callable[[dict[str, Any]], Any]


class JobHandlers:
    def __init__(
        self,
        database: Database,
        sealer: Optional[Sealer],
        registry: Registry,
        plugin_manager: plugins.PluginManager,
    ) -> None:
        self.database = database
        self.sealer = sealer
        self.registry = registry
        self.plugins = plugin_manager

    def all(self) -> dict[str, Handler]:
        return {
            "sync": self.sync,
            "release": self.release,
            "deploy": self.deploy,
            "push": self.push,
            "import": self.import_activity,
            "import_github": self.import_github,
            plugins.INSTALL: self.plugins.install,
            plugins.REMOVE: self.plugins.remove,
            plugins.RESTART: self.plugins.restart,
        }

    def context(self, payload: dict[str, Any]) -> JobContext:
        return JobContext.of(payload, self.database, self.sealer)

    def sync(self, payload: dict[str, Any]) -> Any:
        ctx = self.context(payload)
        request = SyncRequest(**ctx.body)
        result = AppService(self.registry).sync(
            ctx.registry_id, request.credentials, reset=request.reset
        )
        self.import_activity(payload)

        return result

    def release(self, payload: dict[str, Any]) -> Any:
        ctx = self.context(payload)
        result = LifecycleService(self.registry).release(
            ctx.registry_id, ReleaseRequest(**ctx.body)
        )
        self.import_activity(payload)

        return result

    def deploy(self, payload: dict[str, Any]) -> Any:
        ctx = self.context(payload)
        identity = AppIdentity(self.database, self.sealer, settings.PUBLIC_URL)

        return LifecycleService(
            self.registry,
            identity=identity.minter(ctx.organization, ctx.app, ctx.body.get("stage")),
            env=DeployEnv(self.database).for_app(ctx.organization, ctx.app),
        ).deploy(ctx.registry_id, DeployRequest(**ctx.body))

    def push(self, payload: dict[str, Any]) -> Any:
        ctx = self.context(payload)
        result = AppService(self.registry).push(
            ctx.registry_id, PushRequest(**ctx.body)
        )
        self.import_activity(payload)

        return result

    def import_activity(self, payload: dict[str, Any]) -> dict[str, Optional[str]]:
        """Releases and pull requests copied from the code host into the platform's tables."""
        if not payload.get("app_id") or not payload.get("organization_id"):
            return {}

        try:
            url = self.registry.get(payload["registry_id"]).url
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

    def import_github(self, payload: dict[str, Any]) -> Any:
        with self.database.session() as db:
            writes = DirectoryWrites(db, self.sealer)
            creds = writes.credentials_for(
                payload["organization_id"], payload["host_id"]
            )

            if creds is None:
                raise ActionPlatformError("the host has no credentials any more")

            return OrganizationImport(
                writes, payload["organization_id"], self.registry
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
