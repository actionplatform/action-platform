"""Projects: listing, creation, team assignment, deletion."""

from typing import Optional

from fastapi import APIRouter, Header

from app.api.dependencies import (
    CallerDep,
    OrgDep,
    ProjectsDep,
    ProjectsRepoDep,
    allowed,
    manageable,
    project_of,
    requested_org,
    required_org,
)
from app.core.db.models import Organization
from app.schemas import common
from app.schemas import projects as schemas
from app.services.access.caller import Caller
from app.repositories.projects import ProjectsRepository

router = APIRouter(prefix="/api/v1", tags=["management"])


def project_rows(
    directory: ProjectsRepository, caller: Caller, org: Organization, tag: bool
) -> list[schemas.ProjectRow]:
    rows = []

    for p in directory.projects_of(org.id, caller.project_id):
        team = directory.team(org.id, p.team_id) if p.team_id else None
        apps = directory.apps_of(p.id, caller.app_id)
        moments = [p.created_at] + [
            m for a in apps for m in (a.created_at, a.last_synced_at) if m
        ]
        rows.append(
            schemas.ProjectRow(
                id=p.id,
                name=p.name,
                slug=p.slug,
                description=p.description,
                team=common.Named(id=team.id, name=team.name) if team else None,
                apps=[
                    schemas.AppInProject(
                        id=a.id,
                        name=a.name,
                        registry_id=a.registry_id,
                        source_host_id=a.source_host_id,
                        last_synced_at=a.last_synced_at,
                    )
                    for a in apps
                ],
                organization=common.Named(id=org.id, name=org.name) if tag else None,
                created_at=p.created_at,
                updated_at=max(moments),
            )
        )

    return rows


@router.get("/projects")
def projects(
    caller: CallerDep,
    directory: ProjectsRepoDep,
    x_organization: Optional[str] = Header(default=None),
    organization: Optional[str] = None,
) -> list[schemas.ProjectRow]:
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
    body: schemas.CreateProjectRequest,
    caller: CallerDep,
    directory: ProjectsRepoDep,
    x_organization: Optional[str] = Header(default=None),
) -> common.Created:
    org = required_org(caller, x_organization, None)
    manageable(caller, org, "projects")
    project = directory.create_project(org.id, body.name, body.description or "")

    return common.Created(id=project.id, name=project.name, slug=project.slug)


@router.post("/projects/team")
def assign_project_team(
    body: schemas.ProjectTeamRequest,
    caller: CallerDep,
    directory: ProjectsRepoDep,
    x_organization: Optional[str] = Header(default=None),
) -> common.Ok:
    org = required_org(caller, x_organization, None)
    manageable(caller, org, "projects/team")
    directory.assign_project_team(org.id, body.project_id, body.team_id or None)

    return common.Ok()


@router.delete("/projects/{project_id}")
def delete_project(
    project_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    projects: ProjectsDep,
    repositories: bool = False,
) -> common.Removed:
    allowed(caller, org, "project.manage")
    project = project_of(writes, org, project_id)
    removed, deleted = projects.delete(org, project, repositories)

    return common.Removed(removed=removed, repositories=deleted)
