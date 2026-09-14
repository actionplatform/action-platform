"""What an import would do, before it runs: every repository, team and person with its state on the platform."""

from typing import Any

from action_platform.api.services.directory import slugify
from action_platform.api.services.github_import.client import GithubDirectory
from action_platform.api.services.github_import.context import ImportContext


def person_status(
    person: dict[str, Any], user, members: set[str], pending: set[str]
) -> str:
    if user and user.id in members:
        return "member"

    if user:
        return "user"

    if person["email"] in pending:
        return "invited"

    if person["email"]:
        return "invitable"

    return "no_email"


def preview(ctx: ImportContext, github: GithubDirectory, login: str) -> dict[str, Any]:
    known = ctx.known_repositories()
    teams = {t.slug for t in ctx.writes.teams_of(ctx.organization_id)}
    people = github.people(login)
    users = ctx.users_by_email([p["email"] for p in people if p["email"]])
    members = ctx.member_ids()
    pending = {i.email for i, _ in ctx.writes.invitations_of(ctx.organization_id)}

    return {
        "organization": login,
        "repositories": [
            {**r, "imported_as": known.get(r["full_name"].lower())}
            for r in github.repositories(login)
        ],
        "teams": [
            {**t, "exists": t["slug"] in teams or slugify(t["name"]) in teams}
            for t in github.teams(login)
        ],
        "people": [
            {
                **p,
                "status": person_status(
                    p, users.get(p["email"] or ""), members, pending
                ),
            }
            for p in people
        ],
    }
