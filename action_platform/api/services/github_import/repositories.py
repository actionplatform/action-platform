"""Repositories → one project with one app each."""

import logging
from typing import Any

from action_platform.api.core import credentials as auth
from action_platform.api.db.models import Project
from action_platform.api.schemas import SourceCredentials
from action_platform.api.services.directory import Credentials, DirectoryError
from action_platform.api.services.github_import.client import GithubDirectory
from action_platform.api.services.github_import.context import ImportContext
from action_platform.api.services.imports import ImportService
from action_platform.core.exception import ActionPlatformError

log = logging.getLogger("action_platform.import")


def import_repositories(
    ctx: ImportContext,
    github: GithubDirectory,
    creds: Credentials,
    host_id: str,
    login: str,
    wanted: set[str],
) -> dict[str, Project]:
    """Returns owner/name (lowercase) → project for every wanted repository that exists on the platform afterwards."""
    projects: dict[str, Project] = {}

    if not wanted:
        return projects

    known = ctx.known_repositories()
    name, email = ctx.writes.git_author_of(ctx.organization_id)
    credentials = SourceCredentials(
        **{**creds.as_dict(), "author_name": name, "author_email": email}
    )
    seen: set[str] = set()

    for repo in github.repositories(login):
        key = repo["full_name"].lower()

        if key not in wanted:
            continue

        seen.add(key)

        if key in known:
            ctx.summary.skip(repo["full_name"], f"already imported as {known[key]}")
            project = ctx.project_named(known[key])

            if project is not None:
                projects[key] = project

            continue

        try:
            project = import_repository(ctx, repo, credentials, host_id)
        except (ActionPlatformError, DirectoryError) as e:
            ctx.summary.skip(repo["full_name"], str(e))

            continue
        except Exception as e:
            log.exception("import of %s failed", repo["full_name"])
            ctx.summary.skip(repo["full_name"], str(e))

            continue

        projects[key] = project
        ctx.summary.projects.append(project.name)
        ctx.db.commit()

    for key in sorted(wanted - seen):
        ctx.summary.skip(key, "not found on GitHub")

    return projects


def import_repository(
    ctx: ImportContext,
    repo: dict[str, Any],
    credentials: SourceCredentials,
    host_id: str,
) -> Project:
    with auth.git_auth(credentials):
        entry = ctx.registry.add(repo["url"], repo["name"], require_manifest=False)

    project = ctx.project_named(repo["name"]) or ctx.writes.create_project(
        ctx.organization_id, repo["name"], repo.get("description") or ""
    )
    app = ctx.writes.create_app(project.id, entry.id, entry.name, host_id)
    ImportService(ctx.db).sync_all(
        app.id,
        ctx.writes.credentials_for(ctx.organization_id, host_id),
        repo["full_name"],
    )

    return project
