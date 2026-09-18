"""The CI of an app inside a project: which runner it reads, and the runs imported from it."""

from fastapi import APIRouter, HTTPException

from action_platform.core.exception import ActionPlatformError
from app.api.dependencies import (
    CallerDep,
    IntegrationsDep,
    OrgDep,
    ProjectsDep,
    ProjectsRepoDep,
    allowed,
    app_of,
    project_of,
)
from app.schemas import ci as schemas

router = APIRouter(prefix="/api/v1", tags=["management"])


def ci_runs_of(projects, org, app, error=None) -> schemas.CiRuns:
    return schemas.CiRuns(
        link=projects.ci_link(org, app),
        runs=[run_row(r) for r in projects.ci_runs(app)],
        error=error,
    )


def run_row(run) -> schemas.CiRunRow:
    return schemas.CiRunRow(
        id=run.id,
        source=run.source,
        number=run.number,
        status=run.status,
        name=run.name,
        url=run.url,
        branch=run.branch,
        sha=run.sha,
        trigger=run.trigger,
        started_at=run.started_at,
        duration_ms=run.duration_ms,
        synced_at=run.synced_at,
    )


@router.get("/projects/{project_id}/apps/{app_id}/ci")
def ci_runs(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    projects: ProjectsDep,
) -> schemas.CiRuns:
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    return ci_runs_of(projects, org, app)


@router.put("/projects/{project_id}/apps/{app_id}/ci")
def link_ci(
    project_id: str,
    app_id: str,
    body: schemas.CiLinkRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    projects: ProjectsDep,
    integrations: IntegrationsDep,
) -> schemas.CiLink:
    allowed(caller, org, "app.configure", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    if body.ci_host_id and integrations.ci_host(org.id, body.ci_host_id) is None:
        raise HTTPException(404, "ci host not found")

    writes.set_app_ci(app, body.ci_host_id or None, body.job)

    return projects.ci_link(org, app)


@router.post("/projects/{project_id}/apps/{app_id}/ci/sync")
def sync_ci(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    projects: ProjectsDep,
) -> schemas.CiRuns:
    allowed(caller, org, "app.sync", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    try:
        projects.sync_ci(org, app)
        error = None
    except ActionPlatformError as e:
        error = str(e)

    return ci_runs_of(projects, org, app, error)
