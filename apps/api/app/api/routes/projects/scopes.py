"""The scopes of an app: where its releases are deployed, each with a kind and a criticality."""

import json

from fastapi import APIRouter, Depends

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
from app.core.db.models import Scope
from app.repositories.configuration.config_store import ConfigStore
from app.schemas import projects as schemas
from app.services.scopes import ScopesService

router = APIRouter(prefix="/api/v1", tags=["management"])


def _row(scope: Scope) -> schemas.ScopeRow:
    try:
        options = json.loads(scope.target_options or "{}")
    except ValueError:
        options = {}

    return schemas.ScopeRow(
        id=scope.id,
        name=scope.name,
        kind=scope.kind,
        criticality=scope.criticality,
        target=scope.target_kind,
        options=options,
        run_by=scope.run_by,
        url=scope.url,
        derived=scope.derived,
        created_at=scope.created_at,
    )


def _page(service: ScopesService, app) -> schemas.Scopes:
    return schemas.Scopes(
        items=[_row(s) for s in service.of(app)], **ScopesService.vocabulary()
    )


@router.get("/projects/{project_id}/apps/{app_id}/scopes")
def scopes(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    db: DbDep,
    configs: ConfigStore = Depends(get_config_store),
) -> schemas.Scopes:
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    return _page(ScopesService(db, configs), app)


@router.post("/projects/{project_id}/apps/{app_id}/scopes", status_code=201)
def create_scope(
    project_id: str,
    app_id: str,
    body: schemas.ScopeRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    db: DbDep,
    configs: ConfigStore = Depends(get_config_store),
) -> schemas.Scopes:
    allowed(caller, org, "app.configure", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)
    service = ScopesService(db, configs)
    service.create(app, body.model_dump(), caller.user.id)

    return _page(service, app)


@router.put("/projects/{project_id}/apps/{app_id}/scopes/{name}")
def update_scope(
    project_id: str,
    app_id: str,
    name: str,
    body: schemas.ScopeRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    db: DbDep,
    configs: ConfigStore = Depends(get_config_store),
) -> schemas.Scopes:
    allowed(caller, org, "app.configure", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)
    service = ScopesService(db, configs)
    service.update(app, name, body.model_dump())

    return _page(service, app)


@router.delete("/projects/{project_id}/apps/{app_id}/scopes/{name}")
def delete_scope(
    project_id: str,
    app_id: str,
    name: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    db: DbDep,
    queue: QueueDep,
    configs: ConfigStore = Depends(get_config_store),
) -> schemas.Scopes:
    allowed(caller, org, "app.configure", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)
    service = ScopesService(db, configs)
    service.delete(app, name, live=queue.live_deploy(app.id, name) is not None)

    return _page(service, app)
