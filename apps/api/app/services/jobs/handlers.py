"""One callable per job kind, built on the same services the API uses; the worker only claims jobs and dispatches here."""

from __future__ import annotations

import logging

from typing import Any, Optional

from action_platform.core.context import DeployResult
from action_platform.core.exception import ActionPlatformError
from action_platform.settings import settings
from app.core.auth.crypto import Sealer
from app.core.db.database import Database
from app.core.db.models import App, Organization, Project
from app.core.shared.clock import now
from app.core.shared.urls import GitUrl
from app.repositories.configuration.config_store import ConfigStore
from app.repositories.workspace.registry import Registry
from app.schemas import (
    DeployRequest,
    PushRequest,
    ReleaseRequest,
    SourceCredentials,
    SyncRequest,
)
from app.services.activity import ActivityService
from app.services.ci import CiService
from app.services.projects.apps import AppService
from app.services.deployments import DeployEnv, DeploymentRecords
from app.services.integrations.hosts.directory import IntegrationsDirectory
from app.services.projects.organization_import.directory import ImportDirectory
from app.services.deployments.identity import AppIdentity
from app.services.jobs.context import JobContext
from app.services.jobs.registry import JobServices, register
from app.repositories.projects import ProjectsRepository
from app.services.projects import ProjectService
from app.services.projects.organization_import import OrganizationImport
from app.services.deployments import DeploymentsService
from app.services.releases import ReleaseStore, ReleasesService, tag_of
from app.services.workspace.snapshot import SnapshotService
from app.services.workspace.state import GitStateService

log = logging.getLogger(__name__)


class JobHandlers:
    def __init__(
        self, database: Database, sealer: Optional[Sealer], registry: Registry
    ) -> None:
        self.database = database
        self.sealer = sealer
        self.registry = registry
        self.configs = ConfigStore(database)

    @classmethod
    def of(cls, services: JobServices) -> "JobHandlers":
        return cls(services.database, services.sealer, services.registry)

    def context(self, payload: dict[str, Any]) -> JobContext:
        return JobContext.of(payload, self.database, self.sealer)

    def sync(self, payload: dict[str, Any]) -> Any:
        ctx = self.context(payload)
        request = SyncRequest(**ctx.body)
        credentials = request.credentials or self._host_credentials(ctx)
        result = AppService(self.registry).sync(
            ctx.registry_id, credentials, reset=request.reset
        )
        self.import_activity(payload)

        return result

    def _host_credentials(self, ctx: JobContext) -> Optional[SourceCredentials]:
        """The app's source host token, for jobs nobody signed — a webhook's sync."""
        if ctx.app is None or ctx.organization is None or not ctx.app.source_host_id:
            return None

        with self.database.session() as db:
            creds = IntegrationsDirectory(db, self.sealer).credentials_for(
                ctx.organization.id, ctx.app.source_host_id
            )

        return SourceCredentials(**creds.as_dict()) if creds else None

    def release(self, payload: dict[str, Any]) -> Any:
        ctx = self.context(payload)
        request = ReleaseRequest(**ctx.body)
        result = ReleasesService(self.registry).release(ctx.registry_id, request)

        if not request.dry_run and ctx.app is not None:
            self._record_release(ctx, request, result, payload.get("user_id"))

        if not request.dry_run:
            self._snapshot(ctx.registry_id)

        self.import_activity(payload)

        return result

    def _snapshot(self, registry_id: str) -> None:
        try:
            SnapshotService(self.registry, self.configs).take(registry_id)
        except Exception:
            log.warning("snapshot of %s failed", registry_id, exc_info=True)

    def _record_release(
        self, ctx: JobContext, request: ReleaseRequest, result: dict, user_id: Any
    ) -> None:
        with self.database.session() as db:
            store = ReleaseStore(db)
            store.ensure(
                ctx.app.id,
                tag_of(request.component or "", result["next"]),
                "platform",
                name=request.name or None,
                body=result.get("changelog") or None,
                author=DeploymentRecords(db, self.sealer).actor_name(user_id),
                prerelease=bool(result.get("prerelease")),
                published_at=now(),
            )

    def deploy(self, payload: dict[str, Any]) -> Any:
        ctx = self.context(payload)
        identity = AppIdentity(self.database, self.sealer, settings.PUBLIC_URL)
        request = DeployRequest(**ctx.body)
        service = DeploymentsService(
            self.registry,
            identity=identity.minter(
                ctx.organization,
                ctx.app,
                request.stage,
                manages=bool(payload.get("manages")),
            ),
            env=DeployEnv(self.database).for_app(ctx.organization, ctx.app),
        )
        started = now()

        try:
            results = service.deploy(ctx.registry_id, request)
        except ActionPlatformError as e:
            if not request.dry_run:
                self._record_deploy_failure(ctx, payload, request, started, str(e))

            raise

        if not request.dry_run:
            self._record_deploy(ctx, payload, request, started, results)

        return results

    def _record_deploy(
        self,
        ctx: JobContext,
        payload: dict[str, Any],
        request: DeployRequest,
        started: Any,
        results: list[dict],
    ) -> None:
        if ctx.app is None or not payload.get("job_id"):
            return

        with self.database.session() as db:
            records = DeploymentRecords(db, self.sealer)
            records.record_platform(
                db.get(App, ctx.app.id),
                self.configs.config_of(ctx.registry_id),
                [DeployResult(**r) for r in results],
                request.stage,
                payload["job_id"],
                records.actor_name(payload.get("user_id")),
                started,
            )

    def _record_deploy_failure(
        self,
        ctx: JobContext,
        payload: dict[str, Any],
        request: DeployRequest,
        started: Any,
        error: str,
    ) -> None:
        if ctx.app is None or not payload.get("job_id"):
            return

        with self.database.session() as db:
            records = DeploymentRecords(db, self.sealer)
            records.record_failure(
                db.get(App, ctx.app.id),
                self.configs.config_of(ctx.registry_id),
                request.stage,
                request.version,
                payload["job_id"],
                records.actor_name(payload.get("user_id")),
                started,
                error,
            )

    def destroy(self, payload: dict[str, Any]) -> Any:
        """Every stage's stack down, then the app off the platform — the job the web queues for a deletion with cloud cleanup."""
        ctx = self.context(payload)
        identity = AppIdentity(self.database, self.sealer, settings.PUBLIC_URL)
        DeploymentsService(
            self.registry,
            identity=identity.minter(
                ctx.organization, ctx.app, manages=bool(payload.get("manages"))
            ),
            env=DeployEnv(self.database).for_app(ctx.organization, ctx.app),
        ).destroy(ctx.registry_id)

        with self.database.session() as db:
            project = db.get(Project, ctx.app.project_id)
            projects = ProjectService(
                ImportDirectory(db, self.sealer), AppService(self.registry)
            )
            removed, repositories = projects.delete_app(
                ctx.organization, project, ctx.app, bool(ctx.body.get("repository"))
            )

        return {"removed": removed, "repositories": repositories}

    def destroy_project(self, payload: dict[str, Any]) -> Any:
        """Each app's stacks down, then the project off the platform."""
        identity = AppIdentity(self.database, self.sealer, settings.PUBLIC_URL)
        env = DeployEnv(self.database)
        manages = bool(payload.get("manages"))

        with self.database.session() as db:
            organization = db.get(Organization, payload["organization_id"])
            project = db.get(Project, payload["project_id"])
            apps = list(ProjectsRepository(db, self.sealer).apps_of(project.id))

        for app in apps:
            DeploymentsService(
                self.registry,
                identity=identity.minter(organization, app, manages=manages),
                env=env.for_app(organization, app),
            ).destroy(app.registry_id)

        with self.database.session() as db:
            projects = ProjectService(
                ImportDirectory(db, self.sealer), AppService(self.registry)
            )
            removed, repositories = projects.delete(
                organization,
                project,
                bool((payload.get("body") or {}).get("repository")),
            )

        return {"removed": removed, "repositories": repositories}

    def push(self, payload: dict[str, Any]) -> Any:
        ctx = self.context(payload)
        result = AppService(self.registry).push(
            ctx.registry_id, PushRequest(**ctx.body)
        )
        self.import_activity(payload)

        self._snapshot(ctx.registry_id)

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
            directory = IntegrationsDirectory(db, self.sealer)
            app = db.get(App, payload["app_id"])
            creds = directory.credentials_for(
                payload["organization_id"], app.source_host_id
            )
            try:
                tags = GitStateService(self.registry).releases(payload["registry_id"])
            except ActionPlatformError:
                tags = []

            errors = ActivityService(db).sync_all(
                payload["app_id"], creds, GitUrl(url).repo, tags=tags
            )

            try:
                CiService(db, self.sealer).sync_runs(
                    payload["organization_id"], app, GitUrl(url).repo
                )
                errors["ci"] = None
            except ActionPlatformError as e:
                errors["ci"] = str(e)

            try:
                observed = DeploymentRecords(db, self.sealer).sync_observed(
                    payload["organization_id"],
                    app,
                    self.configs.config_of(payload["registry_id"]),
                    GitUrl(url).repo,
                )
                errors["deployments"] = (
                    "; ".join(f"{k}: {v}" for k, v in observed.items() if v) or None
                )
            except ActionPlatformError as e:
                errors["deployments"] = str(e)

            return errors

    def import_github(self, payload: dict[str, Any]) -> Any:
        with self.database.session() as db:
            writes = ImportDirectory(db, self.sealer)
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
register("destroy", lambda s: JobHandlers.of(s).destroy)
register("destroy_project", lambda s: JobHandlers.of(s).destroy_project)
register("import", lambda s: JobHandlers.of(s).import_activity)
register("import_github", lambda s: JobHandlers.of(s).import_github)
