"""Organizations, their members and settings."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select

from action_platform.api.db.models import (
    Member,
    Organization,
    OrganizationSetting,
    User,
)
from action_platform.api.services.common import now
from action_platform.api.services.directory.base import (
    DEFAULT_GIT_AUTHOR,
    EMAIL,
    DirectoryBase,
    DirectoryError,
)
from action_platform.core.access import ROLES, normalize_role


class OrganizationsReads(DirectoryBase):
    def organizations_of(
        self, user_id: str
    ) -> list[tuple[Organization, Optional[str]]]:
        rows = self.db.execute(
            select(Organization, Member.role)
            .join(Member, Member.organization_id == Organization.id)
            .where(Member.user_id == user_id)
            .order_by(Organization.name)
        ).all()

        return [(organization, normalize_role(role)) for organization, role in rows]

    def organization(self, id_or_slug: str) -> Optional[Organization]:
        return self.db.scalar(
            select(Organization).where(
                (Organization.id == id_or_slug) | (Organization.slug == id_or_slug)
            )
        )

    def role_in(self, user_id: str, organization_id: str) -> Optional[str]:
        return normalize_role(
            self.db.scalar(
                select(Member.role).where(
                    Member.user_id == user_id, Member.organization_id == organization_id
                )
            )
        )

    def members_of(self, organization_id: str) -> list[tuple[Member, User]]:
        rows = self.db.execute(
            select(Member, User)
            .join(User, User.id == Member.user_id)
            .where(Member.organization_id == organization_id)
            .order_by(Member.created_at)
        ).all()

        return [(member, user) for member, user in rows]

    def set_member_role(self, organization_id: str, user_id: str, role: str) -> None:
        if role not in ROLES:
            raise DirectoryError(f"role must be one of {', '.join(ROLES)}")

        member = self.db.scalar(
            select(Member).where(
                Member.organization_id == organization_id, Member.user_id == user_id
            )
        )

        if member is None:
            raise DirectoryError("member not found")

        owners = (
            self.db.scalar(
                select(func.count())
                .select_from(Member)
                .where(
                    Member.organization_id == organization_id, Member.role == "owner"
                )
            )
            or 0
        )

        if member.role == "owner" and role != "owner" and owners <= 1:
            raise DirectoryError("the organization needs at least one owner")

        member.role = role
        self.db.flush()

    def git_author_of(self, organization_id: str) -> tuple[str, str]:
        row = self.db.get(OrganizationSetting, organization_id)

        return (
            (row.git_author_name, row.git_author_email) if row else DEFAULT_GIT_AUTHOR
        )


class OrganizationsWrites(OrganizationsReads):
    def remove_member(self, organization_id: str, user_id: str) -> None:
        member = self.db.scalar(
            select(Member).where(
                Member.organization_id == organization_id, Member.user_id == user_id
            )
        )

        if member is None:
            raise DirectoryError("member not found")

        owners = (
            self.db.scalar(
                select(func.count())
                .select_from(Member)
                .where(
                    Member.organization_id == organization_id, Member.role == "owner"
                )
            )
            or 0
        )

        if member.role == "owner" and owners <= 1:
            raise DirectoryError("the organization needs at least one owner")

        for team in self.teams_of(organization_id):
            self.remove_team_member(organization_id, team.id, user_id)

        self.db.delete(member)
        self.db.flush()

    def set_git_author(
        self, organization_id: str, name: str, email: str
    ) -> tuple[str, str]:
        name = name.strip()
        email = email.strip().lower()

        if not name:
            raise DirectoryError("name is required")

        if not EMAIL.match(email):
            raise DirectoryError("enter a valid email")

        row = self.db.get(OrganizationSetting, organization_id)

        if row is None:
            row = OrganizationSetting(
                organization_id=organization_id,
                git_author_name=name,
                git_author_email=email,
            )
            self.db.add(row)
        else:
            row.git_author_name = name
            row.git_author_email = email

        row.updated_at = now()
        self.db.flush()

        return name, email
