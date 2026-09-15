"""What happens to a project's apps: added from a repository, generated from a template, deleted with or without their repositories, kept in step with their host."""

from typing import Any, Optional


from action_platform.core.exception import ActionPlatformError
from app.core.db.models import App, Organization, Project
from app.core.shared.urls import GitUrl
from app.schemas import InitRequest, InstallSpec, SourceCredentials
from app.services.access.enrich import credentials_for
from app.services.activity import ActivityService
from app.services.projects.apps import AppService
from app.services.projects.organization_import.directory import ImportDirectory
from app.core.errors import Invalid


class ProjectService:
    def __init__(self, writes: ImportDirectory, apps: AppService) -> None:
        self.writes = writes
        self.apps = apps
        self.activity = ActivityService(writes.db)

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
            app.id, self.writes.credentials_for(org.id, app.source_host_id), repo
        )

    def _forget(self, registry_id: str) -> None:
        try:
            self.apps.remove(registry_id)
        except ActionPlatformError:
            pass
