"""Apps inside a project: added from a repository or generated, their host, their imported activity."""

from fastapi import APIRouter, HTTPException, Response

from app.api.dependencies import (
    CallerDep,
    OrgDep,
    ProjectsDep,
    IntegrationsDep,
    ProjectsRepoDep,
    QueueDep,
    allowed,
    app_of,
    imports_of,
    project_of,
)
from app.schemas import common
from app.schemas import projects as schemas
from app.services.access.dispatch import Dispatcher

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.post("/projects/{project_id}/apps", status_code=201)
def add_app(
    project_id: str,
    body: schemas.AddAppToProject,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    projects: ProjectsDep,
) -> schemas.AppAdded:
    allowed(caller, org, "project.manage")
    project = project_of(writes, org, project_id)
    app, entry = projects.add_app(org, project, body.url, body.install)

    return schemas.AppAdded(
        id=app.id,
        registry_id=app.registry_id,
        name=app.name,
        installed=entry.get("installed"),
    )


@router.post("/projects/{project_id}/apps/init", status_code=201)
def init_app(
    project_id: str,
    body: schemas.InitAppInProject,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    projects: ProjectsDep,
) -> schemas.AppInitialized:
    allowed(caller, org, "project.manage")
    project = project_of(writes, org, project_id)
    app, result = projects.init_app(
        org, project, body, body.source_host_id, body.template_source
    )

    return schemas.AppInitialized(
        id=app.id,
        registry_id=app.registry_id,
        name=app.name,
        pushed=bool(result.get("pushed")),
    )


@router.delete("/projects/{project_id}/apps/{app_id}")
def delete_app(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    projects: ProjectsDep,
    queue: QueueDep,
    response: Response,
    repository: bool = False,
    cloud: bool = False,
) -> common.Removed:
    """`cloud` tears the deploy stacks down first, on the worker; the app leaves the platform when that job is done (202 with the job id)."""
    allowed(caller, org, "project.manage")
    project = project_of(writes, org, project_id)
    app = writes.app(project.id, app_id)

    if app is None:
        return common.Removed()

    if cloud:
        allowed(caller, org, "app.release", whole_org=False)
        response.status_code = 202

        return common.Removed(
            job=Dispatcher(queue).destroy_app(org, app, caller, repository)
        )

    removed, repositories = projects.delete_app(org, project, app, repository)

    return common.Removed(removed=removed, repositories=repositories)


@router.put("/projects/{project_id}/apps/{app_id}/host")
def set_app_host(
    project_id: str,
    app_id: str,
    body: schemas.AppHostRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    integrations: IntegrationsDep,
) -> schemas.AppHostRequest:
    allowed(caller, org, "app.flow", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    if body.source_host_id and integrations.host(org.id, body.source_host_id) is None:
        raise HTTPException(404, "host not found")

    writes.set_app_host(app, body.source_host_id or None)

    return schemas.AppHostRequest(source_host_id=app.source_host_id)


@router.get("/projects/{project_id}/apps/{app_id}/imports")
def imports(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
) -> schemas.Imports:
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    return imports_of(writes.db, app.id)


@router.post("/projects/{project_id}/apps/{app_id}/imports")
def sync_imports(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    projects: ProjectsDep,
) -> schemas.Imports:
    allowed(caller, org, "app.sync", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)
    errors = projects.sync_activity(org, app)

    return imports_of(writes.db, app.id, errors)
