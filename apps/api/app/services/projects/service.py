"""What happens to a project's apps: added from a repository, generated from a template, deleted with or without their repositories, kept in step with their host."""

from typing import Any, Optional


from action_platform.core.exception import ActionPlatformError
from app.core.db.models import App, Organization, Project
from app.core.shared.urls import GitUrl
from app.schemas import InitRequest, InstallSpec, SourceCredentials
from app.schemas import ci as ci_schemas
from app.schemas import deployments as deploy_schemas
from app.services.access.enrich import credentials_for
from app.services.activity import ActivityService
from app.services.ci import CiService
from app.services.deployments import DeploymentRecords
from app.services.projects.apps import AppService
from app.services.workspace.state import GitStateService
from app.services.projects.organization_import.directory import ImportDirectory
from app.core.errors import Invalid


class ProjectService:
    def __init__(self, writes: ImportDirectory, apps: AppService) -> None:
        self.writes = writes
        self.apps = apps
        self.activity = ActivityService(writes.db)
        self.ci = CiService(writes.db, writes.sealer)
        self.deployments = DeploymentRecords(writes.db, writes.sealer)

    def add_app(
        self,
        org: Organization,
        project: Project,
        url: str,
        install: Optional[InstallSpec],
    ) -> tuple[App, dict[str, Any]]:
        """Clone `url` into the registry, register it in `project`, import its activity."""
        url = url.strip()

        if not url:
            raise Invalid("url is required")

        host_id = self.writes.host_id_for_url(org.id, url)
        kind = GitUrl(url).kind

        if kind and host_id is None:
            raise Invalid(
                f"No {kind} host is connected to this organization. Connect one in Settings so private repositories can be cloned.",
            )

        credentials = credentials_for(self.writes, org, None, {"url": url})
        entry = self.apps.add(url, None, SourceCredentials(**credentials), install)
        app = self.writes.create_app(project.id, entry["id"], entry["name"], host_id)
        self.activity.sync_all(
            app.id, self.writes.credentials_for(org.id, host_id), GitUrl(url).repo
        )

        return app, entry

    def init_app(
        self,
        org: Organization,
        project: Project,
        body: InitRequest,
        source_host_id: Optional[str],
        template_source: Optional[str],
    ) -> tuple[App, dict[str, Any]]:
        """Generate an app from a template with the organization's host and identity, push it, register it."""
        creds = (
            self.writes.credentials_for(org.id, source_host_id)
            if source_host_id
            else None
        )

        if body.push and creds is None:
            raise Invalid("pushing needs a source host")

        name, email = self.writes.git_author_of(org.id)
        request = body.model_copy(
            update={
                "credentials": SourceCredentials(
                    **{
                        **(creds.as_dict() if creds else {}),
                        "author_name": name,
                        "author_email": email,
                    }
                ),
                "source": self.writes.source_spec_by_name(org.id, template_source),
            }
        )
        result = self.apps.init(request)
        app = self.writes.create_app(
            project.id, result["id"], result["name"], source_host_id
        )

        if result.get("pushed") and creds is not None:
            self.activity.sync_all(app.id, creds, GitUrl(result.get("url", "")).repo)

        return app, result

    def delete(
        self, org: Organization, project: Project, repositories: bool
    ) -> tuple[list[str], list[str]]:
        """Remove the project and its apps from the platform; with `repositories`, delete their repositories on the host first."""
        project_apps = self.writes.apps_of(project.id)
        deleted = [
            repo
            for app in project_apps
            if repositories
            and (repo := self.apps.delete_through_host(self.writes, org.id, app))
        ]
        registry_ids = [a.registry_id for a in project_apps]

        for registry_id in registry_ids:
            self._forget(registry_id)

        self.writes.delete_project(org.id, project.id)

        return registry_ids, deleted

    def delete_app(
        self, org: Organization, project: Project, app: App, repository: bool
    ) -> tuple[list[str], list[str]]:
        deleted = (
            self.apps.delete_through_host(self.writes, org.id, app)
            if repository
            else None
        )
        self._forget(app.registry_id)
        self.writes.delete_app(project.id, app.id)

        return [app.registry_id], [deleted] if deleted else []

    def sync_activity(self, org: Organization, app: App) -> dict[str, Optional[str]]:
        """Import releases and pull requests again, attaching a host to the app when its url says which."""
        detail = self.apps.detail(app.registry_id)
        repo = (
            detail.get("source_host", {}).get("repo")
            or GitUrl(detail.get("url", "")).repo
        )

        if app.source_host_id is None:
            host_id = self.writes.host_id_for_url(org.id, detail.get("url", ""))

            if host_id:
                self.writes.set_app_host(app, host_id)

        return self.activity.sync_all(
            app.id,
            self.writes.credentials_for(org.id, app.source_host_id),
            repo,
            tags=self._tags_of(app),
        )

    def _tags_of(self, app: App) -> list[dict]:
        try:
            return GitStateService(self.apps.registry).releases(app.registry_id)
        except ActionPlatformError:
            return []

    def _repo_of(self, app: App) -> str:
        detail = self.apps.detail(app.registry_id)

        return (
            detail.get("source_host", {}).get("repo")
            or GitUrl(detail.get("url", "")).repo
        )

    def sync_ci(self, org: Organization, app: App) -> int:
        return self.ci.sync_runs(org.id, app, self._repo_of(app))

    def ci_link(self, org: Organization, app: App) -> ci_schemas.CiLink:
        return ci_schemas.CiLink(
            kind=self.ci.kind_of(org.id, app),
            ci_host_id=app.ci_host_id,
            job=app.ci_job or "",
        )

    def ci_runs(self, app: App, limit: int = 50, offset: int = 0) -> list:
        return self.ci.runs(app.id, limit, offset)

    def ci_run_count(self, app: App) -> int:
        return self.ci.count(app.id)

    def _config_of(self, app: App):
        return self.apps.configs.config_of(app.registry_id)

    def deployment_targets(self, app: App) -> list[deploy_schemas.TargetRow]:
        return [
            deploy_schemas.TargetRow(
                name=t.name,
                kind=t.kind,
                run_by=t.run_by,
                stages=list(t.stages),
                workflow=t.workflow or None,
                job=t.job or None,
            )
            for t in self._config_of(app).targets
        ]

    def deployment_rows(self, app: App) -> list:
        return self.deployments.list(app.id)

    def sync_deployments(self, org: Organization, app: App) -> dict[str, Optional[str]]:
        return self.deployments.sync_observed(
            org.id, app, self._config_of(app), self._repo_of(app)
        )

    def record_deployment(
        self,
        app: App,
        body: deploy_schemas.RecordDeploymentRequest,
        actor: Optional[str],
    ):
        row = self.deployments.record_manual(
            app,
            self._config_of(app),
            body.target,
            body.version,
            body.stage,
            body.url,
            body.sha,
            body.ok,
            actor,
        )
        self.deployments.verify(app, self._config_of(app))

        return row

    def _forget(self, registry_id: str) -> None:
        try:
            self.apps.remove(registry_id)
        except ActionPlatformError:
            pass
