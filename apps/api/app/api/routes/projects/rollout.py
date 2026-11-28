"""Deployment strategies: which exist, which a scope's targets can run, the steps of a deployment and the controls a person applies between them."""

from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from action_platform.core.rollout import catalog
from app.api.dependencies import (
    CallerDep,
    DbDep,
    OrgDep,
    ProjectsRepoDep,
    QueueDep,
    allowed,
    app_of,
    project_of,
)
from app.api.dependencies.services import get_config_store
from app.core.errors import NotFound
from app.core.shared import people
from app.repositories.configuration.config_store import ConfigStore
from app.repositories.workspace.registry import Registry
from app.repositories.workspace.source import get_registry
from app.schemas import deployments as schemas
from app.services.deployments import (
    AppCiRunners,
    DeployEnv,
    DeploymentsService,
    Rollout,
)
from app.services.scopes import ScopesService

router = APIRouter(prefix="/api/v1", tags=["management"])
APP = "/projects/{project_id}/apps/{app_id}"
DEPLOYMENT = APP + "/deployments/{deployment_id}"
QUEUED: dict[int | str, dict[str, Any]] = {
    202: {"model": schemas.DeploymentControl, "description": "a step was queued"}
}


@router.get("/deploy-strategies")
def deploy_strategies(caller: CallerDep) -> schemas.DeployStrategies:
    return schemas.DeployStrategies.model_validate(catalog())


@router.get(APP + "/scopes/{scope}/strategies")
def scope_strategies(
    project_id: str,
    app_id: str,
    scope: str,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    db: DbDep,
    registry: Registry = Depends(get_registry),
    configs: ConfigStore = Depends(get_config_store),
) -> list[schemas.ScopeStrategy]:
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    if scope not in ScopesService(db, configs).names(app):
        raise NotFound(f"no scope {scope!r}")

    state = request.app.state
    guard = DeployEnv(state.db, state.sealer).of_registry(app.registry_id)
    service = DeploymentsService(
        registry,
        env=dict(guard.env),
        configs=configs,
        ci=AppCiRunners(db, state.sealer).of_registry(app.registry_id),
        guard=guard,
    )

    return [
        schemas.ScopeStrategy.model_validate(row)
        for row in service.strategies(app.registry_id, scope)
    ]


@router.get(DEPLOYMENT + "/steps")
def deployment_steps(
    project_id: str,
    app_id: str,
    deployment_id: str,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    queue: QueueDep,
) -> list[schemas.StepRow]:
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)
    _, steps = Rollout(request.app.state.db, queue).state(app.id, deployment_id)

    return [schemas.StepRow.model_validate(s, from_attributes=True) for s in steps]


@router.get(DEPLOYMENT + "/events")
def deployment_events(
    project_id: str,
    app_id: str,
    deployment_id: str,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    queue: QueueDep,
) -> list[schemas.DeploymentEventRow]:
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    return [
        schemas.DeploymentEventRow.model_validate(e, from_attributes=True)
        for e in Rollout(request.app.state.db, queue).events(app.id, deployment_id)
    ]


def _control(
    action: str,
    project_id: str,
    app_id: str,
    deployment_id: str,
    request: Request,
    response: Response,
    org: Any,
    caller: Any,
    writes: Any,
    queue: Any,
) -> schemas.DeploymentControl:
    allowed(caller, org, "app.release", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)
    rollout = Rollout(request.app.state.db, queue)
    answer = rollout.control(
        app,
        org.id,
        deployment_id,
        action,
        user_id=caller.user.id,
        actor=people.label(caller.user),
    )
    row, steps = rollout.state(app.id, deployment_id)

    if answer["queued"]:
        response.status_code = 202

    return schemas.DeploymentControl(
        deployment=schemas.DeploymentRow.model_validate(row, from_attributes=True),
        steps=[schemas.StepRow.model_validate(s, from_attributes=True) for s in steps],
        queued=answer["queued"],
        live=answer["live"],
    )


@router.post(DEPLOYMENT + "/promote", responses=QUEUED)
def promote_deployment(
    project_id: str,
    app_id: str,
    deployment_id: str,
    request: Request,
    response: Response,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    queue: QueueDep,
) -> schemas.DeploymentControl:
    return _control(
        "promote",
        project_id,
        app_id,
        deployment_id,
        request,
        response,
        org,
        caller,
        writes,
        queue,
    )


@router.post(DEPLOYMENT + "/pause", responses=QUEUED)
def pause_deployment(
    project_id: str,
    app_id: str,
    deployment_id: str,
    request: Request,
    response: Response,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    queue: QueueDep,
) -> schemas.DeploymentControl:
    return _control(
        "pause",
        project_id,
        app_id,
        deployment_id,
        request,
        response,
        org,
        caller,
        writes,
        queue,
    )


@router.post(DEPLOYMENT + "/resume", responses=QUEUED)
def resume_deployment(
    project_id: str,
    app_id: str,
    deployment_id: str,
    request: Request,
    response: Response,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    queue: QueueDep,
) -> schemas.DeploymentControl:
    return _control(
        "resume",
        project_id,
        app_id,
        deployment_id,
        request,
        response,
        org,
        caller,
        writes,
        queue,
    )


@router.post(DEPLOYMENT + "/abort", responses=QUEUED)
def abort_deployment(
    project_id: str,
    app_id: str,
    deployment_id: str,
    request: Request,
    response: Response,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    queue: QueueDep,
) -> schemas.DeploymentControl:
    return _control(
        "abort",
        project_id,
        app_id,
        deployment_id,
        request,
        response,
        org,
        caller,
        writes,
        queue,
    )
