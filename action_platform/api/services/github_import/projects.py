"""GitHub Projects → platform projects; the repositories linked to a project become its apps."""

from action_platform.api.db.models import Project
from action_platform.api.services.github_import.client import GithubDirectory
from action_platform.api.services.github_import.context import ImportContext


def import_projects(
    ctx: ImportContext, github: GithubDirectory, login: str, wanted: set[int]
) -> dict[str, Project]:
    """Returns owner/name (lowercase) → the platform project a repository belongs to through a wanted GitHub Project."""
    targets: dict[str, Project] = {}

    if not wanted:
        return targets

    for remote in github.projects(login):
        if remote["number"] not in wanted:
            continue

        project = ctx.project_named(remote["title"])

        if project is None:
            project = ctx.writes.create_project(
                ctx.organization_id, remote["title"], remote.get("description") or ""
            )
            ctx.summary.projects.append(project.name)
        else:
            ctx.summary.skip(
                f"project {remote['title']}", "already exists, apps added to it"
            )

        for repo in remote["repositories"]:
            targets.setdefault(repo.lower(), project)

    ctx.db.commit()

    return targets
