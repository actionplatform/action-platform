"""Teams and who is in them."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from app.core.db.models import (
    Project,
    Team,
    TeamMember,
    User,
)
from app.core.shared.clock import now
from app.core.shared.ids import new_id, slugify
from app.repositories.base import (
    DirectoryBase,
    DirectoryError,
)


class TeamsReads(DirectoryBase):
    def team(self, organization_id: str, team_id: str) -> Optional[Team]:
        return self.db.scalar(
            select(Team).where(
                Team.id == team_id, Team.organization_id == organization_id
            )
        )

    def teams_of(self, organization_id: str) -> list[Team]:
        return list(
            self.db.scalars(
                select(Team)
                .where(Team.organization_id == organization_id)
                .order_by(Team.name)
            )
        )

    def team_members_of(self, team_id: str) -> list[User]:
        return list(
            self.db.scalars(
                select(User)
                .join(TeamMember, TeamMember.user_id == User.id)
                .where(TeamMember.team_id == team_id)
                .order_by(User.name)
            )
        )

    def team_projects_of(self, team_id: str) -> list[Project]:
        return list(
            self.db.scalars(
                select(Project).where(Project.team_id == team_id).order_by(Project.name)
            )
        )

    def create_team(
        self, organization_id: str, name: str, description: str = ""
    ) -> Team:
        name = name.strip()

        if not name:
            raise DirectoryError("name is required")

        slug = slugify(name)

        if self.db.scalar(
            select(Team.id).where(
                Team.organization_id == organization_id, Team.slug == slug
            )
        ):
            raise DirectoryError(f"a team named {name} already exists")

        team = Team(
            id=new_id(),
            organization_id=organization_id,
            name=name,
            slug=slug,
            description=description.strip() or None,
            created_at=now(),
        )
        self.db.add(team)
        self.db.flush()

        return team

    def add_team_member(self, organization_id: str, team_id: str, user_id: str) -> None:
        if self.team(organization_id, team_id) is None:
            raise DirectoryError("team not found")

        if self.role_in(user_id, organization_id) is None:
            raise DirectoryError("not a member of the organization")

        if self.db.scalar(
            select(TeamMember.id).where(
                TeamMember.team_id == team_id, TeamMember.user_id == user_id
            )
        ):
            return

        self.db.add(
            TeamMember(id=new_id(), team_id=team_id, user_id=user_id, created_at=now())
        )
        self.db.flush()


class TeamsWrites(TeamsReads):
    def update_team(
        self, organization_id: str, team_id: str, name: str, description: str
    ) -> Team:
        team = self.team(organization_id, team_id)

        if team is None:
            raise DirectoryError("team not found")

        name = name.strip()

        if not name:
            raise DirectoryError("name is required")

        team.name = name
        team.slug = slugify(name)
        team.description = description.strip() or None
        self.db.flush()

        return team

    def delete_team(self, organization_id: str, team_id: str) -> None:
        team = self.team(organization_id, team_id)

        if team is None:
            raise DirectoryError("team not found")

        for project in self.team_projects_of(team.id):
            project.team_id = None

        self.db.delete(team)
        self.db.flush()

    def remove_team_member(
        self, organization_id: str, team_id: str, user_id: str
    ) -> None:
        if self.team(organization_id, team_id) is None:
            raise DirectoryError("team not found")

        row = self.db.scalar(
            select(TeamMember).where(
                TeamMember.team_id == team_id, TeamMember.user_id == user_id
            )
        )

        if row is not None:
            self.db.delete(row)
            self.db.flush()
