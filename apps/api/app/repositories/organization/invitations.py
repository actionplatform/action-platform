"""Invitations into an organization."""

from __future__ import annotations

import json
from typing import Optional

from sqlalchemy import select

from action_platform.core.access import ROLES
from app.core.db.models import (
    Invitation,
    Member,
    Organization,
    User,
)
from app.core.shared.clock import now
from app.core.shared.ids import new_id
from app.repositories.base import (
    EMAIL,
    INVITATION_TTL,
    DirectoryBase,
    DirectoryError,
)


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
        self,
        organization_id: str,
        inviter_id: str,
        email: str,
        role: str,
        team_ids: Optional[list[str]] = None,
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
                self.add_invitation_teams(invitation, team_ids or [])

                return invitation

        return self._new_invitation(
            organization_id, inviter_id, role, team_ids, email=email
        )

    def create_login_invitation(
        self,
        organization_id: str,
        inviter_id: str,
        host_kind: str,
        login: str,
        role: str,
        team_ids: Optional[list[str]] = None,
    ) -> Invitation:
        """An invitation for whoever proves they own `login` on the code host, for people the host shows no email for."""
        login = login.strip()

        if role not in ROLES:
            raise DirectoryError(f"role must be one of {', '.join(ROLES)}")

        if not login:
            raise DirectoryError("enter a login")

        for invitation, _ in self.invitations_of(organization_id):
            if (
                invitation.host_kind == host_kind
                and (invitation.host_login or "").lower() == login.lower()
            ):
                self.add_invitation_teams(invitation, team_ids or [])

                return invitation

        return self._new_invitation(
            organization_id,
            inviter_id,
            role,
            team_ids,
            host_kind=host_kind,
            host_login=login,
        )

    def _new_invitation(
        self,
        organization_id: str,
        inviter_id: str,
        role: str,
        team_ids: Optional[list[str]],
        email: Optional[str] = None,
        host_kind: Optional[str] = None,
        host_login: Optional[str] = None,
    ) -> Invitation:
        moment = now()
        invitation = Invitation(
            id=new_id(),
            organization_id=organization_id,
            email=email,
            host_kind=host_kind,
            host_login=host_login,
            team_ids=json.dumps(sorted(set(team_ids))) if team_ids else None,
            role=role,
            status="pending",
            expires_at=moment + INVITATION_TTL,
            created_at=moment,
            inviter_id=inviter_id,
        )
        self.db.add(invitation)
        self.db.flush()

        return invitation

    def add_invitation_teams(self, invitation: Invitation, team_ids: list[str]) -> None:
        """The teams the person joins on accepting, added to those already waiting."""
        waiting = set(invitation_team_ids(invitation))

        if not set(team_ids) - waiting:
            return

        invitation.team_ids = json.dumps(sorted(waiting | set(team_ids)))
        self.db.flush()

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

    def accept_invitation(
        self, id: str, user: User, verified_login: Optional[str] = None
    ) -> Organization:
        """Make `user` a member with the invitation's role and put them in its teams. A login invitation needs `verified_login`, the host login the person just proved."""
        found = self.invitation(id)

        if found is None:
            raise DirectoryError("invitation not found")

        invitation, _, organization = found

        if invitation.status != "pending":
            raise DirectoryError(f"invitation {invitation.status}")

        if invitation.expires_at < now():
            raise DirectoryError("invitation expired")

        if invitation.host_login:
            if verified_login is None:
                raise DirectoryError(
                    f"this invitation is for @{invitation.host_login} on "
                    f"{invitation.host_kind}: verify the account to join"
                )

            if verified_login.lower() != invitation.host_login.lower():
                raise DirectoryError(
                    f"this invitation is for @{invitation.host_login}, "
                    f"not @{verified_login}"
                )
        elif invitation.email != user.email.lower():
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
            self.db.flush()

        for team_id in invitation_team_ids(invitation):
            if self.team(organization.id, team_id) is not None:
                self.add_team_member(organization.id, team_id, user.id)

        invitation.status = "accepted"
        self.db.flush()

        return organization


def invitation_team_ids(invitation: Invitation) -> list[str]:
    try:
        ids = json.loads(invitation.team_ids or "[]")
    except ValueError:
        return []

    return [i for i in ids if isinstance(i, str)]
