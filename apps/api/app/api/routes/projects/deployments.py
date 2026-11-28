"""The deployments of an app inside a project: its targets, what arrived at each, whoever executed it."""

from typing import Optional, Union

from fastapi import APIRouter

from action_platform.core.exception import ActionPlatformError
from app.api.dependencies import (
    CallerDep,
    DeploymentRecordsDep,
    OrgDep,
    ProjectsRepoDep,
    allowed,
    app_of,
    project_of,
)
from app.core.errors import Invalid
from app.core.shared import people
from app.schemas import deployments as schemas
from app.schemas.common import page_bounds

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/projects/{project_id}/apps/{app_id}/deployments")
def deployments(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    records: DeploymentRecordsDep,
    page: Optional[int] = None,
    per: int = 10,
) -> Union[schemas.Deployments, schemas.DeploymentsPage]:
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)
    answer = records.page(app)

    if page is None:
        return answer

    page, per, offset = page_bounds(page, per)

    return schemas.DeploymentsPage(
        targets=answer.targets,
        deployments=answer.deployments[offset : offset + per],
        error=answer.error,
        total=len(answer.deployments),
        page=page,
        per=per,
    )


@router.post("/projects/{project_id}/apps/{app_id}/deployments/sync")
def sync_deployments(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    records: DeploymentRecordsDep,
) -> schemas.Deployments:
    allowed(caller, org, "app.sync", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    try:
        errors = records.sync(org.id, app)
        error = "; ".join(f"{k}: {v}" for k, v in errors.items() if v) or None
    except ActionPlatformError as e:
        error = str(e)

    return records.page(app, error)


@router.post("/projects/{project_id}/apps/{app_id}/deployments", status_code=201)
def record_deployment(
    project_id: str,
    app_id: str,
    body: schemas.RecordDeploymentRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    records: DeploymentRecordsDep,
) -> schemas.DeploymentRow:
    allowed(caller, org, "app.release", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    if not body.version.strip():
        raise Invalid("a deployment ships a release: version is required")

    try:
        row = records.record(app, body, people.label(caller.user))
    except ActionPlatformError as e:
        raise Invalid(str(e)) from e

    return schemas.DeploymentRow.model_validate(row, from_attributes=True)
