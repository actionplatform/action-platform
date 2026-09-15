"""One callable per job kind, built on the same services the API uses; the worker only claims jobs and dispatches here."""

from __future__ import annotations

from typing import Any, Optional

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
from app.services.projects.apps import AppService
from app.services.deployments import DeployEnv
from app.services.directory import DirectoryService, DirectoryWrites
from app.services.deployments.identity import AppIdentity
from app.services.jobs.context import JobContext
from app.services.jobs.registry import JobServices, register
from app.services.projects.organization_import import OrganizationImport
from app.services.deployments import DeploymentsService
from app.services.releases import ReleasesService


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

    @classmethod
    def of(cls, services: JobServices) -> "JobHandlers":
        return cls(
            services.database, services.sealer, services.registry, services.plugins
        )

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
        result = ReleasesService(self.registry).release(
            ctx.registry_id, ReleaseRequest(**ctx.body)
        )
        self.import_activity(payload)

        return result

    def deploy(self, payload: dict[str, Any]) -> Any:
        ctx = self.context(payload)
        identity = AppIdentity(self.database, self.sealer, settings.PUBLIC_URL)

        return DeploymentsService(
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


register("sync", lambda s: JobHandlers.of(s).sync)
register("release", lambda s: JobHandlers.of(s).release)
register("deploy", lambda s: JobHandlers.of(s).deploy)
register("push", lambda s: JobHandlers.of(s).push)
register("import", lambda s: JobHandlers.of(s).import_activity)
register("import_github", lambda s: JobHandlers.of(s).import_github)
register(plugins.INSTALL, lambda s: s.plugins.install)
register(plugins.REMOVE, lambda s: s.plugins.remove)
register(plugins.RESTART, lambda s: s.plugins.restart)
