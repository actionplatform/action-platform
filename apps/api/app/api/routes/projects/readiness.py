"""Whether a release of an app can reach a stage: what the worker last checked, and a new check on request."""

from fastapi import APIRouter, Depends, Request

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
from app.schemas import projects as schemas
from app.api.dependencies.services import get_config_store
from app.core.errors import Invalid
from app.repositories.configuration.config_store import ConfigStore
from app.services.releases import ReadinessRequests
from app.services.scopes import ScopesService

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/projects/{project_id}/apps/{app_id}/releases/{tag:path}/readiness")
def readiness(
    project_id: str,
    app_id: str,
    tag: str,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    queue: QueueDep,
) -> list[schemas.ReadinessRow]:
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    return [
        schemas.ReadinessRow.model_validate(row)
        for row in ReadinessRequests(request.app.state.db, queue).of(app, tag)
    ]


@router.post("/projects/{project_id}/apps/{app_id}/releases/{tag:path}/readiness")
def check_readiness(
    project_id: str,
    app_id: str,
    tag: str,
    body: schemas.ReadinessRequest,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    queue: QueueDep,
    db: DbDep,
    configs: ConfigStore = Depends(get_config_store),
) -> schemas.ReadinessQueued:
    allowed(caller, org, "app.release", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)
    scopes = ScopesService(db, configs).names(app)

    if body.stage and body.stage not in scopes:
        raise Invalid(
            f"no scope {body.stage!r} (scopes: {', '.join(scopes) or 'none'})"
        )

    if not scopes:
        raise Invalid("no scope, no readiness — create the app's scopes first")

    stages = (body.stage,) if body.stage else tuple(scopes)
    requests = ReadinessRequests(request.app.state.db, queue)
    release_id, release_tag = requests.release_of(app, tag)
    jobs = requests.request(
        org.id,
        app,
        release_id,
        release_tag,
        stages=stages,
        user_id=caller.user.id,
        manages=caller.allows(org.id, "org.manage")[0]
        and not (caller.project_id or caller.app_id),
    )

    return schemas.ReadinessQueued(
        jobs=jobs,
        readiness=[
            schemas.ReadinessRow.model_validate(row) for row in requests.of(app, tag)
        ],
    )
