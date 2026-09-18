"""The organization's dashboard and a release's timeline."""

from fastapi import APIRouter, Request

from app.api.dependencies import (
    CallerDep,
    DbDep,
    OrgDep,
    ProjectsRepoDep,
    app_of,
    project_of,
)
from app.schemas import insights as schemas
from app.services.insights import InsightsService

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/dashboard")
def dashboard(
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    db: DbDep,
    fresh: bool = False,
) -> schemas.Dashboard:
    data = InsightsService(db).dashboard(
        org.id, caller.project_id, caller.app_id, fresh=fresh
    )

    return schemas.Dashboard(**data)


@router.get("/projects/{project_id}/apps/{app_id}/releases/{tag:path}/timeline")
def timeline(
    project_id: str,
    app_id: str,
    tag: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    db: DbDep,
) -> schemas.Timeline:
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)
    found = InsightsService(db).timeline(app.id, tag)

    return schemas.Timeline(
        release=schemas.ReleaseRow.model_validate(
            found["release"], from_attributes=True
        ),
        previous=schemas.ReleaseRow.model_validate(
            found["previous"], from_attributes=True
        )
        if found["previous"]
        else None,
        pull_requests=[
            schemas.PullRequestRow.model_validate(p, from_attributes=True)
            for p in found["pull_requests"]
        ],
        ci_runs=[
            schemas.CiRunRow.model_validate(c, from_attributes=True)
            for c in found["ci_runs"]
        ],
        deployments=[
            schemas.DeploymentRow.model_validate(d, from_attributes=True)
            for d in found["deployments"]
        ],
    )
