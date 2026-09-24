"""What the remote tools share: the argument types and how a project or an app is found from what an agent passes."""

from __future__ import annotations

from typing import Annotated, Optional

from pydantic import Field

from action_platform.core.exception import ActionPlatformError
from action_platform.mcp import schemas
from action_platform.remote.client import Remote

AppId = Annotated[str, Field(description="App id from list_apps")]
ProjectId = Annotated[
    str,
    Field(description="Project id or slug from list_projects; apps live in projects"),
]
OrgId = Annotated[
    Optional[str],
    Field(
        description="Organization id or slug; needed only when the token spans every organization (see whoami)"
    ),
]


def repo_key(url: str) -> str:
    """owner/name of a git URL, so https://github.com/a/b.git and git@github.com:a/b match."""
    text = url.strip().removesuffix(".git").rstrip("/")
    text = text.replace(":", "/")
    parts = [p for p in text.split("/") if p]

    return "/".join(parts[-2:]).lower() if len(parts) >= 2 else ""


def org_of(row: schemas.ProjectRow) -> Optional[str]:
    """The organization a project row names when the token spans every organization; None when it does not need saying."""
    return row.organization.id if row.organization else None


def project_of(
    remote: Remote, project: str, organization: Optional[str] = None
) -> schemas.ProjectRow:
    """The project row for an id or slug; a name the platform does not know is an error the agent can read."""
    for row in remote.projects(organization=organization):
        if project in (row.id, row.slug):
            return row

    raise ActionPlatformError(f"no project {project!r}: list_projects shows them")


def app_in_project(
    remote: Remote, app_id: str
) -> tuple[schemas.ProjectRow, schemas.AppRef]:
    """(project, app) for an app id from list_apps, which is the registry id the workspace tools use."""
    for project in remote.projects():
        for app in project.apps:
            if app_id in (app.registry_id, app.id):
                return project, app

    raise ActionPlatformError(f"no app {app_id!r}: list_apps shows them")
