"""What every step of an import shares: the platform organization, its directory and registry, and the summary being built."""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from action_platform.api.db.models import App, Project, User
from action_platform.api.repositories.registry import Registry
from action_platform.api.services.directory import DirectoryWrites
from action_platform.core.exception import ActionPlatformError
from action_platform.api.services.shared.urls import GitUrl


@dataclass
class Summary:
    projects: list[str] = field(default_factory=list)
    apps: list[str] = field(default_factory=list)
    teams: list[str] = field(default_factory=list)
    members: list[str] = field(default_factory=list)
    invitations: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def skip(self, what: str, why: str) -> None:
        self.skipped.append(f"{what}: {why}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "projects": self.projects,
            "apps": self.apps,
            "teams": self.teams,
            "members": self.members,
            "invitations": self.invitations,
            "skipped": self.skipped,
        }


@dataclass
class ImportContext:
    writes: DirectoryWrites
    registry: Registry
    organization_id: str
    summary: Summary = field(default_factory=Summary)

    @property
    def db(self):
        return self.writes.db

    def known_repositories(self) -> dict[str, str]:
        """owner/name (lowercase) → project name, for every app already in the organization."""
        rows = self.db.execute(
            select(App.registry_id, Project.name)
            .join(Project, Project.id == App.project_id)
            .where(Project.organization_id == self.organization_id)
        ).all()
        known = {}

        for registry_id, project_name in rows:
            try:
                url = self.registry.get(registry_id).url
            except ActionPlatformError:
                continue

            repo = GitUrl(url).repo

            if repo:
                known[repo.lower()] = project_name

        return known

    def users_by_email(self, emails: list[str]) -> dict[str, User]:
        if not emails:
            return {}

        rows = self.db.scalars(select(User).where(User.email.in_(emails)))

        return {u.email.lower(): u for u in rows}

    def member_ids(self) -> set[str]:
        return {user.id for _, user in self.writes.members_of(self.organization_id)}

    def project_named(self, name: str) -> Project | None:
        return self.db.scalar(
            select(Project).where(
                Project.organization_id == self.organization_id, Project.name == name
            )
        )
