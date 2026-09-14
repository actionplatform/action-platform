"""People → members (when they already have an account) or invitations (when GitHub shows an email)."""

from action_platform.api.db.models import Member, User
from action_platform.api.services.directory import DirectoryError, new_id, now
from action_platform.api.services.github_import.client import GithubDirectory
from action_platform.api.services.github_import.context import ImportContext


def import_people(
    ctx: ImportContext,
    github: GithubDirectory,
    inviter_id: str,
    login: str,
    wanted: set[str],
    role: str,
) -> dict[str, User]:
    """Returns GitHub login (lowercase) → platform user for every person with an account, wanted or not, so teams can be filled."""
    people = github.people(login) if wanted else []
    users = ctx.users_by_email([p["email"] for p in people if p["email"]])
    members = ctx.member_ids()
    by_login: dict[str, User] = {}

    for person in people:
        user = users.get(person["email"] or "")
        key = person["login"].lower()

        if user:
            by_login[key] = user

        if key not in wanted or (user and user.id in members):
            continue

        if user:
            add_member(ctx, user, role)
            members.add(user.id)
            ctx.summary.members.append(person["login"])

            continue

        if not person["email"]:
            ctx.summary.skip(
                person["login"], "no public email on GitHub; invite by email"
            )

            continue

        try:
            ctx.writes.create_invitation(
                ctx.organization_id, inviter_id, person["email"], role
            )
            ctx.summary.invitations.append(person["email"])
        except DirectoryError as e:
            ctx.summary.skip(person["login"], str(e))

    return by_login


def add_member(ctx: ImportContext, user: User, role: str) -> None:
    ctx.db.add(
        Member(
            id=new_id(),
            organization_id=ctx.organization_id,
            user_id=user.id,
            role=role,
            created_at=now(),
        )
    )
    ctx.db.flush()
