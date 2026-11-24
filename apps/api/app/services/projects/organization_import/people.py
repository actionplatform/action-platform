"""People → members (when they already have an account), invitations by email (when the host shows one) or by host login."""

from dataclasses import dataclass, field

from action_platform.core import access
from app.core.db.models import Invitation, Member, User
from app.core.shared.clock import now
from app.core.shared.ids import new_id
from app.repositories.base import DirectoryError
from app.services.projects.organization_import.step import ImportStep

HOST_ROLES = ("org_admin", "team_maintainer", "member")


@dataclass
class RoleMapping:
    """The platform role each person arrives with: an override for the login, else the mapping of their host role, else `default`."""

    default: str = "developer"
    by_host_role: dict[str, str] = field(default_factory=dict)
    by_login: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        unknown = set(self.by_host_role) - set(HOST_ROLES)

        if unknown:
            raise DirectoryError(
                f"roles maps {', '.join(HOST_ROLES)}, not {', '.join(sorted(unknown))}"
            )

        self.by_login = {k.lower(): v for k, v in self.by_login.items()}
        allowed = [r for r in access.ROLES if r != "owner"]

        for role in [
            self.default,
            *self.by_host_role.values(),
            *self.by_login.values(),
        ]:
            if role not in allowed:
                raise DirectoryError(f"role must be one of {', '.join(allowed)}")

    def of(self, person: dict) -> str:
        return self.by_login.get(person["login"].lower()) or self.by_host_role.get(
            person.get("role") or "member", self.default
        )


@dataclass
class People:
    """What the people step leaves for the teams step: the platform user and the pending invitation behind each host login (lowercase)."""

    users: dict[str, User] = field(default_factory=dict)
    invitations: dict[str, Invitation] = field(default_factory=dict)


class PeopleImporter(ImportStep):
    def run(
        self,
        inviter_id: str,
        login: str,
        wanted: set[str],
        roles: RoleMapping,
        with_teams: bool = False,
    ) -> People:
        """Every person with an account or a pending invitation, wanted or not, so teams can be filled."""
        people = self.host.people(login) if wanted or with_teams else []
        users = self.ctx.users_by_email([p["email"] for p in people if p["email"]])
        pending = self.ctx.pending_invitations(self.host.kind)
        members = self.ctx.member_ids()
        can_prove = self.ctx.can_prove_login(self.host.kind)
        found = People()

        for person in people:
            user = users.get(person["email"] or "")
            key = person["login"].lower()
            invitation = pending.get(person["email"] or "") or pending.get(f"@{key}")

            if user:
                found.users[key] = user
            elif invitation:
                found.invitations[key] = invitation

            if key not in wanted or (user and user.id in members) or invitation:
                continue

            role = roles.of(person)

            if user:
                self._add_member(user, role)
                members.add(user.id)
                self.summary.members.append(person["login"])
            elif person["email"]:
                self._invite(found, key, inviter_id, person, role)
            elif self.host.kind == "bitbucket" and not person.get("user_id"):
                self.summary.skip(
                    person["login"],
                    "Bitbucket gave no account id to bind the invitation to",
                )
            elif can_prove:
                self._invite_login(found, key, inviter_id, person, role)
            else:
                self.summary.skip(
                    person["login"],
                    "no public email, and the platform has no OAuth app for this host "
                    "to verify the login; invite by email",
                )

        return found

    def _add_member(self, user: User, role: str) -> None:
        self.ctx.db.add(
            Member(
                id=new_id(),
                organization_id=self.organization_id,
                user_id=user.id,
                role=role,
                created_at=now(),
            )
        )
        self.ctx.db.flush()

    def _invite(
        self, found: People, key: str, inviter_id: str, person: dict, role: str
    ) -> None:
        try:
            invitation = self.writes.create_invitation(
                self.organization_id, inviter_id, person["email"], role
            )
            found.invitations[key] = invitation
            self.summary.invitations.append(person["email"])

            if self.ctx.invites is not None and invitation.emailed_at is None:
                self.ctx.invites.send(self.writes, invitation.id)
        except DirectoryError as e:
            self.summary.skip(person["login"], str(e))

    def _invite_login(
        self, found: People, key: str, inviter_id: str, person: dict, role: str
    ) -> None:
        try:
            found.invitations[key] = self.writes.create_login_invitation(
                self.organization_id,
                inviter_id,
                self.host.kind,
                person["login"],
                role,
                host_user_id=person.get("user_id"),
            )
            self.summary.login_invitations.append(f"@{person['login']}")
        except DirectoryError as e:
            self.summary.skip(person["login"], str(e))
