"""What an import would do, before it runs: every repository, team and person with its state on the platform."""

from typing import Any

from action_platform.api.services.directory import slugify
from action_platform.api.services.github_import.client import GithubDirectory
from action_platform.api.services.github_import.context import ImportContext
from action_platform.core.exception import ProviderError


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
    problems: list[str] = []
    members_refused = False

    try:
        repositories = github.repositories(login)
    except ProviderError as e:
        repositories = []
        problems.append(
            f"repositories: {e}. The GitHub App must be installed on {login} with access to its repositories "
            "(Install the app on GitHub, pick the organization, all repositories); an OAuth token needs the repo scope."
        )

    try:
        remote_teams = github.teams(login)
    except ProviderError as e:
        remote_teams = []
        members_refused = True
        problems.append(f"teams: {e}")

    try:
        people = github.people(login)
    except ProviderError as e:
        people = []
        members_refused = True
        problems.append(f"people: {e}")

    if members_refused:
        problems.append(
            "Teams and people need the GitHub App permission Organization › Members (read) — "
            "update it under the app's settings on GitHub and accept it on the organization — "
            "or a token with the read:org scope."
        )
    users = ctx.users_by_email([p["email"] for p in people if p["email"]])
    members = ctx.member_ids()
    pending = {i.email for i, _ in ctx.writes.invitations_of(ctx.organization_id)}

    return {
        "organization": login,
        "repositories": [
            {**r, "imported_as": known.get(r["full_name"].lower())}
            for r in repositories
        ],
        "teams": [
            {**t, "exists": t["slug"] in teams or slugify(t["name"]) in teams}
            for t in remote_teams
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
        "problems": problems,
    }
