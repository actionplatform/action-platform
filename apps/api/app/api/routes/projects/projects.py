"""Projects: listing, creation, team assignment, deletion."""

from typing import Optional

from fastapi import APIRouter, Header, Response

from app.api.dependencies import (
    CallerDep,
    OrgDep,
    ProjectsDep,
    ProjectsRepoDep,
    ProjectViewDep,
    QueueDep,
    allowed,
    manageable,
    project_of,
    requested_org,
    required_org,
)
from app.schemas import common
from app.schemas import projects as schemas
from app.services.access.job_dispatcher import JobDispatcher

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/projects")
def projects(
    caller: CallerDep,
    view: ProjectViewDep,
    x_organization: Optional[str] = Header(default=None),
    organization: Optional[str] = None,
) -> list[schemas.ProjectRow]:
    org = requested_org(caller, x_organization, organization)

    if org is None:
        return view.across(caller)

    return view.rows(caller, org)


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
    queue: QueueDep,
    response: Response,
    repositories: bool = False,
    cloud: bool = False,
) -> common.Removed:
    """`cloud` tears every app's deploy stacks down first, on the worker; the project leaves the platform when that job is done (202 with the job id)."""
    allowed(caller, org, "project.manage")
    project = project_of(writes, org, project_id)

    if cloud:
        allowed(caller, org, "app.release", whole_org=False)
        response.status_code = 202

        return common.Removed(
            job=JobDispatcher(queue).destroy_project(org, project, caller, repositories)
        )

    removed, deleted = projects.delete(org, project, repositories)

    return common.Removed(removed=removed, repositories=deleted)
