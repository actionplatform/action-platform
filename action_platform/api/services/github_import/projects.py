"""GitHub Projects → platform projects; the repositories linked to a project become its apps."""

from typing import Optional

from action_platform.api.db.models import Project
from action_platform.api.services.directory import DirectoryError
from action_platform.api.services.github_import.client import GithubDirectory
from action_platform.api.services.github_import.context import ImportContext


def import_projects(
    ctx: ImportContext,
    github: GithubDirectory,
    login: str,
    wanted: dict[int, Optional[str]],
) -> dict[str, Project]:
    """Returns owner/name (lowercase) → the platform project a repository belongs to through a wanted GitHub Project. `wanted` maps the GitHub project number to the platform project its apps go into, or None for one named after it."""
    targets: dict[str, Project] = {}

    if not wanted:
        return targets

    for remote in github.projects(login):
        if remote["number"] not in wanted:
            continue

        project = target_for(ctx, remote, wanted[remote["number"]])

        for repo in remote["repositories"]:
            targets.setdefault(repo.lower(), project)

    ctx.db.commit()

    return targets


def target_for(ctx: ImportContext, remote: dict, chosen: Optional[str]) -> Project:
    if chosen:
        project = ctx.writes.project(ctx.organization_id, chosen)

        if project is None:
            raise DirectoryError(f"project {chosen} not found")

        ctx.summary.skip(f"project {remote['title']}", f"apps added to {project.name}")

        return project

    project = ctx.project_named(remote["title"])

    if project is not None:
        ctx.summary.skip(
            f"project {remote['title']}", "already exists, apps added to it"
        )

        return project

    project = ctx.writes.create_project(
        ctx.organization_id, remote["title"], remote.get("description") or ""
    )
    ctx.summary.projects.append(project.name)

    return project
