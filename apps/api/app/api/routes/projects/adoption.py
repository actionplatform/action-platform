"""Adoption of a project's apps: where each one stands, and the job that opens their install pull requests."""

from fastapi import APIRouter

from app.api.dependencies import (
    CallerDep,
    OrgDep,
    ProjectsRepoDep,
    QueueDep,
    allowed,
    project_of,
)
from app.schemas import projects as schemas
from app.services.projects.adoption import Adoption

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/projects/{project_id}/adoption")
def adoption(
    project_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    queue: QueueDep,
) -> list[schemas.AdoptionRow]:
    project = project_of(writes, org, project_id)
    service = Adoption(writes, queue)
    apps = service.apps_of(project, [], lambda a: caller.within_reach(a.id, project.id))

    return [schemas.AdoptionRow.model_validate(row) for row in service.states(apps)]


@router.post("/projects/{project_id}/install", status_code=202)
def install(
    project_id: str,
    body: schemas.ProjectInstallRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    queue: QueueDep,
) -> schemas.InstallQueued:
    """A dry run (the default) answers each app's plan; `dry_run: false` commits on `chore/<code>` and opens a pull request per repository. Both run on the worker."""
    allowed(caller, org, "project.manage")
    project = project_of(writes, org, project_id)
    service = Adoption(writes, queue)
    apps = service.apps_of(
        project, body.apps, lambda a: caller.within_reach(a.id, project.id)
    )
    job = service.enqueue(org, project, apps, caller.user.id, body.model_dump())

    return schemas.InstallQueued(job=job.id, poll=f"/api/v1/jobs/{job.id}")
