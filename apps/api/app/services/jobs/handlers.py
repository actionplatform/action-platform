"""One callable per job kind, built on the same services the API uses; the worker only claims jobs and dispatches here."""

from __future__ import annotations

import logging

from typing import Any, Optional

from action_platform.core.context import DeployResult
from action_platform.core.exception import ActionPlatformError
from action_platform.core.scopes import shape_of
from action_platform.settings import settings
from app.core.auth.crypto import Sealer
from app.core.db.database import Database
from app.core.db.models import App, Organization, Project, Release
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
from app.services.organization.removal import OrganizationRemoval
from app.services.scopes import ScopesService
from app.services.deployments import DeploymentsService
from app.services.releases import (
    ReadinessRequests,
    ReadinessService,
    ReleaseStore,
    ReleasesService,
    tag_of,
)
from app.repositories.releases import ReadinessStore
from app.repositories.scopes import ScopeStore
from app.services.jobs.queue import JobQueue
from app.services.workspace.snapshot import SnapshotService
from app.services.workspace import git_auth as auth
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
        """The app's source host token, for jobs nobody signed — a webhook's sync, a deploy or a tear-down whose clone is gone."""
        return self._app_credentials(ctx.organization, ctx.app)

    def _app_credentials(
        self, organization: Optional[Organization], app: Optional[App]
    ) -> Optional[SourceCredentials]:
        if app is None or organization is None or not app.source_host_id:
            return None

        with self.database.session() as db:
            creds = IntegrationsDirectory(db, self.sealer).credentials_for(
                organization.id, app.source_host_id
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
            release = store.ensure(
                ctx.app.id,
                tag_of(request.component or "", result["next"]),
                "platform",
                shape=shape_of(result["next"], request.branch),
                name=request.name or None,
                body=result.get("changelog") or None,
                author=DeploymentRecords(db, self.sealer).actor_name(user_id),
                prerelease=bool(result.get("prerelease")),
                published_at=now(),
            )
            db.flush()
            release_id, tag = release.id, release.tag

        with self.database.session() as db:
            stages = tuple(
                ScopesService(db, self.configs).names(db.get(App, ctx.app.id))
            )

        if not stages:
            return

        ReadinessRequests(self.database, JobQueue(self.database)).request(
            ctx.organization.id,
            ctx.app,
            release_id,
            tag,
            stages=stages,
            user_id=user_id,
            manages=bool(ctx.payload.get("manages")),
        )

    def readiness(self, payload: dict[str, Any]) -> Any:
        ctx = self.context(payload)
        tag = str(ctx.body.get("tag") or "")
        stage = str(ctx.body.get("stage") or "")

        if not stage:
            raise ActionPlatformError("readiness needs a scope")

        with self.database.session() as db:
            release = ReleaseStore(db).get(ctx.app.id, tag)

            if release is None:
                raise ActionPlatformError(f"no release {tag} for this app")

            ReadinessStore(db).running(release.id, stage)
            release_id, shape = release.id, release.shape

        scopes = self._scopes(ctx.app)

        identity = AppIdentity(self.database, self.sealer, settings.api.public_url)
        credentials = self._host_credentials(ctx)
        service = ReadinessService(
            self.registry,
            identity=identity.minter(
                ctx.organization, ctx.app, stage, manages=bool(payload.get("manages"))
            ),
            env=DeployEnv(self.database).for_app(ctx.organization, ctx.app),
            credentials=credentials,
        )

        try:
            with auth.git_auth(credentials):
                checks = service.check(
                    ctx.registry_id, tag, stage, shape=shape, scopes=scopes
                )
        except Exception as e:
            with self.database.session() as db:
                ReadinessStore(db).failed(
                    db.get(Release, release_id), stage, str(e), payload.get("job_id")
                )

            raise

        with self.database.session() as db:
            row = ReadinessStore(db).done(
                db.get(Release, release_id), stage, checks, payload.get("job_id")
            )

            return {
                "tag": tag,
                "stage": stage,
                "ok": row.ok,
                "checks": ReadinessStore.checks_of(row),
            }

    def deploy(self, payload: dict[str, Any]) -> Any:
        ctx = self.context(payload)
        identity = AppIdentity(self.database, self.sealer, settings.api.public_url)
        request = DeployRequest(**ctx.body)
        credentials = self._host_credentials(ctx)
        service = DeploymentsService(
            self.registry,
            identity=identity.minter(
                ctx.organization,
                ctx.app,
                request.stage,
                manages=bool(payload.get("manages")),
            ),
            env=DeployEnv(self.database).for_app(ctx.organization, ctx.app),
            credentials=credentials,
        )
        started = now()

        try:
            with auth.git_auth(credentials):
                results = service.deploy(ctx.registry_id, request)
        except ActionPlatformError as e:
            if not request.dry_run:
                self._record_deploy_failure(ctx, payload, request, started, str(e))

            raise

        if not request.dry_run:
            self._record_deploy(ctx, payload, request, started, results)

        return results

    def _scopes(self, app: Optional[App]) -> list[dict]:
        if app is None:
            return []

        with self.database.session() as db:
            return [
                ScopeStore.as_toml(spec)
                for spec in ScopesService(db, self.configs).specs(db.get(App, app.id))
            ]

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
        identity = AppIdentity(self.database, self.sealer, settings.api.public_url)
        with auth.git_auth(self._host_credentials(ctx)):
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

    def destroy_organization(self, payload: dict[str, Any]) -> Any:
        """Every app's stacks down, then the organization and everything it owned off the platform."""
        identity = AppIdentity(self.database, self.sealer, settings.api.public_url)
        env = DeployEnv(self.database)
        body = payload.get("body") or {}

        with self.database.session() as db:
            organization = db.get(Organization, payload["organization_id"])
            repo = ProjectsRepository(db, self.sealer)
            apps = [
                app
                for project in repo.projects_of(organization.id)
                for app in repo.apps_of(project.id)
            ]

        for app in apps:
            try:
                with auth.git_auth(self._app_credentials(organization, app)):
                    DeploymentsService(
                        self.registry,
                        identity=identity.minter(organization, app, manages=True),
                        env=env.for_app(organization, app),
                    ).destroy(app.registry_id)
            except ActionPlatformError as e:
                log.warning("tear down of %s skipped: %s", app.name, e)

        with self.database.session() as db:
            return OrganizationRemoval(db, self.sealer, self.registry).delete(
                db.get(Organization, organization.id),
                str(payload.get("user_id")),
                str(body.get("confirm") or ""),
                bool(body.get("repository")),
            )

    def destroy_project(self, payload: dict[str, Any]) -> Any:
        """Each app's stacks down, then the project off the platform."""
        identity = AppIdentity(self.database, self.sealer, settings.api.public_url)
        env = DeployEnv(self.database)
        manages = bool(payload.get("manages"))

        with self.database.session() as db:
            organization = db.get(Organization, payload["organization_id"])
            project = db.get(Project, payload["project_id"])
            apps = list(ProjectsRepository(db, self.sealer).apps_of(project.id))

        for app in apps:
            with auth.git_auth(self._app_credentials(organization, app)):
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
register("destroy_organization", lambda s: JobHandlers.of(s).destroy_organization)
register("readiness", lambda s: JobHandlers.of(s).readiness)
register("release", lambda s: JobHandlers.of(s).release)
register("deploy", lambda s: JobHandlers.of(s).deploy)
register("push", lambda s: JobHandlers.of(s).push)
register("destroy", lambda s: JobHandlers.of(s).destroy)
register("destroy_project", lambda s: JobHandlers.of(s).destroy_project)
register("import", lambda s: JobHandlers.of(s).import_activity)
register("import_github", lambda s: JobHandlers.of(s).import_github)
