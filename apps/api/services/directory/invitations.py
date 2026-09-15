"""Invitations into an organization."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from action_platform_api.core.db.models import (
    Invitation,
    Member,
    Organization,
    User,
)
from action_platform_api.core.shared.clock import now
from action_platform_api.core.shared.ids import new_id
from action_platform_api.services.directory.base import (
    EMAIL,
    INVITATION_TTL,
    DirectoryBase,
    DirectoryError,
)
from action_platform.core.access import ROLES


class InvitationsReads(DirectoryBase):
    pass


class InvitationsWrites(InvitationsReads):
    def invitations_of(self, organization_id: str) -> list[tuple[Invitation, User]]:
        rows = self.db.execute(
            select(Invitation, User)
            .join(User, User.id == Invitation.inviter_id)
            .where(
                Invitation.organization_id == organization_id,
                Invitation.status == "pending",
                Invitation.expires_at > now(),
            )
            .order_by(Invitation.created_at)
        ).all()

        return [(invitation, user) for invitation, user in rows]

    def create_invitation(
        self, organization_id: str, inviter_id: str, email: str, role: str
    ) -> Invitation:
        email = email.strip().lower()

        if role not in ROLES:
            raise DirectoryError(f"role must be one of {', '.join(ROLES)}")

        if not EMAIL.match(email):
            raise DirectoryError("enter a valid email")

        already = self.db.scalar(
            select(Member.id)
            .join(User, User.id == Member.user_id)
            .where(Member.organization_id == organization_id, User.email == email)
        )

        if already:
            raise DirectoryError("already a member")

        for invitation, _ in self.invitations_of(organization_id):
            if invitation.email == email:
                return invitation

        moment = now()
        invitation = Invitation(
            id=new_id(),
            organization_id=organization_id,
            email=email,
            role=role,
            status="pending",
            expires_at=moment + INVITATION_TTL,
            created_at=moment,
            inviter_id=inviter_id,
        )
        self.db.add(invitation)
        self.db.flush()

        return invitation

    def cancel_invitation(self, organization_id: str, id: str) -> None:
        invitation = self.db.scalar(
            select(Invitation).where(
                Invitation.id == id, Invitation.organization_id == organization_id
            )
        )

        if invitation is not None:
            invitation.status = "canceled"
            self.db.flush()

    def invitation(self, id: str) -> Optional[tuple[Invitation, User, Organization]]:
        row = self.db.execute(
            select(Invitation, User, Organization)
            .join(User, User.id == Invitation.inviter_id)
            .join(Organization, Organization.id == Invitation.organization_id)
            .where(Invitation.id == id)
        ).first()

        return (row[0], row[1], row[2]) if row else None

    def accept_invitation(self, id: str, user: User) -> Organization:
        found = self.invitation(id)

        if found is None:
            raise DirectoryError("invitation not found")

        invitation, _, organization = found

        if invitation.status != "pending":
            raise DirectoryError(f"invitation {invitation.status}")

        if invitation.expires_at < now():
            raise DirectoryError("invitation expired")

        if invitation.email != user.email.lower():
            raise DirectoryError(f"this invitation is for {invitation.email}")

        if self.role_in(user.id, organization.id) is None:
            self.db.add(
                Member(
                    id=new_id(),
                    organization_id=organization.id,
                    user_id=user.id,
                    role=invitation.role or "developer",
                    created_at=now(),
                )
            )

        invitation.status = "accepted"
        self.db.flush()

        return organization
