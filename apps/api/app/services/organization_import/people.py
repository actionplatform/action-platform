"""People → members (when they already have an account) or invitations (when the host shows an email)."""

from app.core.db.models import Member, User
from app.services.directory import DirectoryError, new_id, now
from app.services.organization_import.step import ImportStep


class PeopleImporter(ImportStep):
    def run(
        self, inviter_id: str, login: str, wanted: set[str], role: str
    ) -> dict[str, User]:
        """Returns host login (lowercase) → platform user for every person with an account, wanted or not, so teams can be filled."""
        people = self.host.people(login) if wanted else []
        users = self.ctx.users_by_email([p["email"] for p in people if p["email"]])
        members = self.ctx.member_ids()
        by_login: dict[str, User] = {}

        for person in people:
            user = users.get(person["email"] or "")
            key = person["login"].lower()

            if user:
                by_login[key] = user

            if key not in wanted or (user and user.id in members):
                continue

            if user:
                self._add_member(user, role)
                members.add(user.id)
                self.summary.members.append(person["login"])
            elif not person["email"]:
                self.summary.skip(
                    person["login"], "no public email on the host; invite by email"
                )
            else:
                self._invite(inviter_id, person, role)

        return by_login

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

    def _invite(self, inviter_id: str, person: dict, role: str) -> None:
        try:
            self.writes.create_invitation(
                self.organization_id, inviter_id, person["email"], role
            )
            self.summary.invitations.append(person["email"])
        except DirectoryError as e:
            self.summary.skip(person["login"], str(e))
