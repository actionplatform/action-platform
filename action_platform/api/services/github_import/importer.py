"""Entry point: preview or run an import into one platform organization."""

from typing import Any, Optional

from action_platform.api.repositories.registry import Registry
from action_platform.api.services.directory import (
    Credentials,
    DirectoryError,
    DirectoryWrites,
)
from action_platform.api.services.github_import import client
from action_platform.api.services.github_import.context import ImportContext
from action_platform.api.services.github_import.people import import_people
from action_platform.api.services.github_import.preview import preview
from action_platform.api.services.github_import.projects import import_projects
from action_platform.api.services.github_import.repositories import (
    import_repositories,
)
from action_platform.api.services.github_import.teams import import_teams
from action_platform.core import access


class GithubImport:
    def __init__(
        self, writes: DirectoryWrites, organization_id: str, registry: Registry
    ) -> None:
        self.ctx = ImportContext(writes, registry, organization_id)

    def preview(self, creds: Credentials, login: str) -> dict[str, Any]:
        return preview(self.ctx, client.GithubDirectory(creds), login)

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

        into = None

        if project_id:
            into = self.ctx.writes.project(self.ctx.organization_id, project_id)

            if into is None:
                raise DirectoryError("project not found")

        github = client.GithubDirectory(creds)
        targets = import_projects(self.ctx, github, login, projects or {})
        wanted_repos = {r.lower() for r in repositories} | set(targets)
        by_repo = import_repositories(
            self.ctx, github, creds, host_id, login, wanted_repos, into, targets
        )
        users = import_people(
            self.ctx, github, inviter_id, login, {p.lower() for p in people}, role
        )
        import_teams(
            self.ctx, github, login, {t.lower() for t in teams}, by_repo, users
        )

        return self.ctx.summary.as_dict()
