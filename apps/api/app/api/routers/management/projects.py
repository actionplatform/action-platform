"""Projects: listing, creation, team assignment, deletion."""

from typing import Optional

from fastapi import APIRouter, Depends, Header

from action_platform.core.exception import ActionPlatformError
from app.api.dependencies import (
    allowed,
    get_app_service,
    get_caller,
    get_directory,
    get_writes,
    manageable,
    org_of,
    project_of,
    required_org,
    requested_org,
)
from app.core.db.models import Organization
from app.schemas import directory as dschemas
from app.schemas import management as schemas
from app.services.access.caller import Caller
from app.services.apps import AppService
from app.services.directory import DirectoryService, DirectoryWrites


router = APIRouter(prefix="/api/v1", tags=["management"])


def project_rows(
    directory: DirectoryService, caller: Caller, org: Organization, tag: bool
) -> list[dschemas.ProjectRow]:
    rows = []

    for p in directory.projects_of(org.id, caller.project_id):
        team = directory.team(org.id, p.team_id) if p.team_id else None
        apps = directory.apps_of(p.id, caller.app_id)
        moments = [p.created_at] + [
            m for a in apps for m in (a.created_at, a.last_synced_at) if m
        ]
        rows.append(
            dschemas.ProjectRow(
                id=p.id,
                name=p.name,
                slug=p.slug,
                description=p.description,
                team=dschemas.Named(id=team.id, name=team.name) if team else None,
                apps=[
                    dschemas.AppInProject(
                        id=a.id,
                        name=a.name,
                        registry_id=a.registry_id,
                        source_host_id=a.source_host_id,
                        last_synced_at=a.last_synced_at,
                    )
                    for a in apps
                ],
                organization=dschemas.Named(id=org.id, name=org.name) if tag else None,
                created_at=p.created_at,
                updated_at=max(moments),
            )
        )

    return rows


@router.get("/projects")
def projects(
    x_organization: Optional[str] = Header(default=None),
    organization: Optional[str] = None,
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
) -> list[dschemas.ProjectRow]:
    org = requested_org(caller, x_organization, organization)

    if org is None:
        return [
            row
            for o, _ in caller.organizations
            for row in project_rows(directory, caller, o, True)
        ]

    return project_rows(directory, caller, org, False)


@router.post("/projects", status_code=201)
def create_project(
    body: dschemas.CreateProjectRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
) -> dschemas.Created:
    org = required_org(caller, x_organization, None)
    manageable(caller, org, "projects")
    project = directory.create_project(org.id, body.name, body.description or "")

    return dschemas.Created(id=project.id, name=project.name, slug=project.slug)


@router.post("/projects/team")
def assign_project_team(
    body: dschemas.ProjectTeamRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
) -> dschemas.Ok:
    org = required_org(caller, x_organization, None)
    manageable(caller, org, "projects/team")
    directory.assign_project_team(org.id, body.project_id, body.team_id or None)

    return dschemas.Ok()


@router.delete("/projects/{project_id}")
def delete_project(
    project_id: str,
    repositories: bool = False,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
    apps: AppService = Depends(get_app_service),
) -> schemas.Removed:
    org = org_of(caller, x_organization)
    allowed(caller, org, "project.manage")
    project = project_of(writes, org, project_id)
    project_apps = writes.apps_of(project.id)
    deleted = []

    if repositories:
        for app in project_apps:
            repo = apps.delete_through_host(writes, org.id, app)

            if repo:
                deleted.append(repo)

    registry_ids = [a.registry_id for a in project_apps]

    for registry_id in registry_ids:
        try:
            apps.remove(registry_id)
        except ActionPlatformError:
            pass

    writes.delete_project(org.id, project_id)

    return schemas.Removed(removed=registry_ids, repositories=deleted)
