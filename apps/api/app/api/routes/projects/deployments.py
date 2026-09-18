"""The deployments of an app inside a project: its targets, what arrived at each, whoever executed it."""

from fastapi import APIRouter

from action_platform.core.exception import ActionPlatformError
from app.api.dependencies import (
    CallerDep,
    OrgDep,
    ProjectsDep,
    ProjectsRepoDep,
    allowed,
    app_of,
    project_of,
)
from app.core.errors import Invalid
from app.schemas import deployments as schemas

router = APIRouter(prefix="/api/v1", tags=["management"])


def deployment_row(row) -> schemas.DeploymentRow:
    return schemas.DeploymentRow(
        id=row.id,
        target=row.target,
        kind=row.kind,
        stage=row.stage,
        version=row.version,
        sha=row.sha,
        status=row.status,
        executor=row.executor,
        job_id=row.job_id,
        ci_run_id=row.ci_run_id,
        url=row.url,
        actor=row.actor,
        error=row.error,
        started_at=row.started_at,
        finished_at=row.finished_at,
        verified_at=row.verified_at,
        synced_at=row.synced_at,
    )


def deployments_of(projects, app, error=None) -> schemas.Deployments:
    return schemas.Deployments(
        targets=projects.deployment_targets(app),
        deployments=[deployment_row(r) for r in projects.deployment_rows(app)],
        error=error,
    )


@router.get("/projects/{project_id}/apps/{app_id}/deployments")
def deployments(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    projects: ProjectsDep,
) -> schemas.Deployments:
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    return deployments_of(projects, app)


@router.post("/projects/{project_id}/apps/{app_id}/deployments/sync")
def sync_deployments(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    projects: ProjectsDep,
) -> schemas.Deployments:
    allowed(caller, org, "app.sync", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    try:
        errors = projects.sync_deployments(org, app)
        error = "; ".join(f"{k}: {v}" for k, v in errors.items() if v) or None
    except ActionPlatformError as e:
        error = str(e)

    return deployments_of(projects, app, error)


@router.post("/projects/{project_id}/apps/{app_id}/deployments", status_code=201)
def record_deployment(
    project_id: str,
    app_id: str,
    body: schemas.RecordDeploymentRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    projects: ProjectsDep,
) -> schemas.DeploymentRow:
    allowed(caller, org, "app.release", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    if not body.version.strip():
        raise Invalid("a deployment ships a release: version is required")

    try:
        row = projects.record_deployment(app, body, caller.user.name)
    except ActionPlatformError as e:
        raise Invalid(str(e)) from e

    return deployment_row(row)
