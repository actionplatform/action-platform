"""Teams → teams, with the members who are already in the organization and the projects of their repositories."""

from action_platform.api.db.models import Project, User
from action_platform.api.services.directory import slugify
from action_platform.api.services.github_import.client import GithubDirectory
from action_platform.api.services.github_import.context import ImportContext


def import_teams(
    ctx: ImportContext,
    github: GithubDirectory,
    login: str,
    wanted: set[str],
    projects_by_repo: dict[str, Project],
    user_by_login: dict[str, User],
) -> None:
    if not wanted:
        return

    existing = {t.slug: t for t in ctx.writes.teams_of(ctx.organization_id)}
    members = ctx.member_ids()
    shared = len({p.id for p in projects_by_repo.values()}) < len(projects_by_repo)

    for remote in github.teams(login):
        if remote["slug"].lower() not in wanted:
            continue

        team = existing.get(remote["slug"]) or existing.get(slugify(remote["name"]))

        if team is None:
            team = ctx.writes.create_team(
                ctx.organization_id, remote["name"], remote.get("description") or ""
            )
            ctx.summary.teams.append(team.name)
        else:
            ctx.summary.skip(f"team {remote['name']}", "already exists, updated")

        in_team = {u.id for u in ctx.writes.team_members_of(team.id)}

        for member_login in remote["members"]:
            user = user_by_login.get(member_login.lower())

            if user is None or user.id not in members or user.id in in_team:
                continue

            ctx.writes.add_team_member(ctx.organization_id, team.id, user.id)
            in_team.add(user.id)

        for repo in remote["repositories"]:
            project = projects_by_repo.get(repo.lower())

            if project is not None and project.team_id is None and not shared:
                ctx.writes.assign_project_team(ctx.organization_id, project.id, team.id)
