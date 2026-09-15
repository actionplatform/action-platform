"""Entry point: preview or run an import into one platform organization."""

from typing import Any, Optional

from action_platform_api.repositories.registry import Registry
from action_platform_api.services.directory import (
    Credentials,
    DirectoryError,
    DirectoryWrites,
)
from action_platform_api.services.organization_import import client
from action_platform_api.services.organization_import.context import ImportContext
from action_platform_api.services.organization_import.people import PeopleImporter
from action_platform_api.services.organization_import.preview import ImportPreview
from action_platform_api.services.organization_import.projects import ProjectImporter
from action_platform_api.services.organization_import.repositories import (
    RepositoryImporter,
)
from action_platform_api.services.organization_import.teams import TeamImporter
from action_platform.core import access


class OrganizationImport:
    def __init__(
        self, writes: DirectoryWrites, organization_id: str, registry: Registry
    ) -> None:
        self.ctx = ImportContext(writes, registry, organization_id)

    def preview(self, creds: Credentials, login: str) -> dict[str, Any]:
        return ImportPreview(self.ctx, client.GithubDirectory(creds)).run(login)

    def run(
        self,
        creds: Credentials,
        host_id: str,
        inviter_id: str,
        login: str,
        repositories: list[str],
        teams: list[str],
        people: list[str],
        role: str,
        project_id: Optional[str] = None,
        projects: Optional[dict[int, Optional[str]]] = None,
    ) -> dict[str, Any]:
        if role not in access.ROLES:
            raise DirectoryError(f"role must be one of {', '.join(access.ROLES)}")

        into = self._project(project_id)
        host = client.GithubDirectory(creds)
        targets = ProjectImporter(self.ctx, host).run(login, projects or {})
        by_repo = RepositoryImporter(self.ctx, host).run(
            creds,
            host_id,
            login,
            {r.lower() for r in repositories} | set(targets),
            into,
            targets,
        )
        users = PeopleImporter(self.ctx, host).run(
            inviter_id, login, {p.lower() for p in people}, role
        )
        TeamImporter(self.ctx, host).run(
            login, {t.lower() for t in teams}, by_repo, users
        )

        return self.ctx.summary.as_dict()

    def _project(self, project_id: Optional[str]):
        if not project_id:
            return None

        project = self.ctx.writes.project(self.ctx.organization_id, project_id)

        if project is None:
            raise DirectoryError("project not found")

        return project
