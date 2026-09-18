"""The CI of an app inside a project: which runner it reads, and the runs imported from it."""

from fastapi import APIRouter, HTTPException

from action_platform.core.exception import ActionPlatformError
from app.api.dependencies import (
    CallerDep,
    CiDep,
    IntegrationsDep,
    OrgDep,
    ProjectsRepoDep,
    allowed,
    app_of,
    project_of,
)
from app.schemas import ci as schemas

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/projects/{project_id}/apps/{app_id}/ci")
def ci_runs(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    ci: CiDep,
    page: int = 1,
    per: int = 10,
) -> schemas.CiRuns:
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    return ci.page(org.id, app, page, per)


@router.put("/projects/{project_id}/apps/{app_id}/ci")
def link_ci(
    project_id: str,
    app_id: str,
    body: schemas.CiLinkRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    ci: CiDep,
    integrations: IntegrationsDep,
) -> schemas.CiLink:
    allowed(caller, org, "app.configure", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    if body.ci_host_id and integrations.ci_host(org.id, body.ci_host_id) is None:
        raise HTTPException(404, "ci host not found")

    writes.set_app_ci(app, body.ci_host_id or None, body.job)

    return ci.link(org.id, app)


@router.post("/projects/{project_id}/apps/{app_id}/ci/sync")
def sync_ci(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    ci: CiDep,
    page: int = 1,
    per: int = 10,
) -> schemas.CiRuns:
    allowed(caller, org, "app.sync", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    try:
        ci.sync(org.id, app)
        error = None
    except ActionPlatformError as e:
        error = str(e)

    return ci.page(org.id, app, page, per, error)
