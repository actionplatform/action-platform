"""What every step of an import shares: the platform organization, its directory and registry, and the summary being built."""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from action_platform.core.exception import ActionPlatformError
from app.core.db.models import App, Invitation, Project, User
from app.core.shared.urls import GitUrl
from app.repositories.workspace.registry import Registry
from app.services.projects.organization_import.directory import ImportDirectory


@dataclass
class Summary:
    projects: list[str] = field(default_factory=list)
    apps: list[str] = field(default_factory=list)
    teams: list[str] = field(default_factory=list)
    members: list[str] = field(default_factory=list)
    invitations: list[str] = field(default_factory=list)
    login_invitations: list[str] = field(default_factory=list)
    teams_waiting: dict[str, list[str]] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)

    def skip(self, what: str, why: str) -> None:
        self.skipped.append(f"{what}: {why}")

    def wait(self, who: str, team: str) -> None:
        waiting = self.teams_waiting.setdefault(who, [])

        if team not in waiting:
            waiting.append(team)

    def as_dict(self) -> dict[str, Any]:
        return {
            "projects": self.projects,
            "apps": self.apps,
            "teams": self.teams,
            "members": self.members,
            "invitations": self.invitations,
            "login_invitations": self.login_invitations,
            "waiting": [
                f"{who} → {', '.join(teams)}"
                for who, teams in self.teams_waiting.items()
            ],
            "skipped": self.skipped,
        }


@dataclass
class ImportContext:
    writes: ImportDirectory
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

    def pending_invitations(self, host_kind: str) -> dict[str, Invitation]:
        """Pending invitations of the organization keyed by email and by host login (both lowercase)."""
        found: dict[str, Invitation] = {}

        for invitation, _ in self.writes.invitations_of(self.organization_id):
            if invitation.email:
                found[invitation.email.lower()] = invitation

            if invitation.host_login and invitation.host_kind == host_kind:
                found[f"@{invitation.host_login.lower()}"] = invitation

        return found

    def can_prove_login(self, host_kind: str) -> bool:
        """Whether an invitee can verify a login on this host: the platform has its OAuth app."""
        return self.writes.oauth_app(host_kind) is not None
