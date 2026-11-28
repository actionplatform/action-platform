"""Apps inside a project: added from a repository or generated, their host, their imported activity."""

from typing import Union

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
    pull_requests_page,
    releases_page,
    project_of,
)
from app.schemas import common
from app.schemas import projects as schemas
from app.services.access.job_dispatcher import JobDispatcher

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
        report=entry.get("report"),
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


@router.delete(
    "/projects/{project_id}/apps/{app_id}",
    status_code=204,
    response_model=None,
    responses={202: {"model": common.Removed}},
)
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
) -> Union[Response, common.Removed]:
    """`cloud` tears the deploy stacks down first, on the worker; the app leaves the platform when that job is done (202 with the job id)."""
    allowed(caller, org, "project.manage")
    project = project_of(writes, org, project_id)
    app = writes.app(project.id, app_id)

    if app is None:
        return Response(status_code=204)

    if cloud:
        allowed(caller, org, "app.release", whole_org=False)
        response.status_code = 202

        return common.Removed(
            job=JobDispatcher(queue).destroy_app(org, app, caller, repository)
        )

    projects.delete_app(org, project, app, repository)

    return Response(status_code=204)


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


@router.get("/projects/{project_id}/apps/{app_id}/releases")
def releases(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    page: int = 1,
    per: int = 10,
) -> schemas.ReleasePage:
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    return releases_page(writes.db, app.id, page, per)


@router.get("/projects/{project_id}/apps/{app_id}/pull-requests")
def pull_requests(
    project_id: str,
    app_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: ProjectsRepoDep,
    page: int = 1,
    per: int = 10,
) -> schemas.PullRequestPage:
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    return pull_requests_page(writes.db, app.id, page, per)


@router.post("/projects/{project_id}/apps/{app_id}/imports", status_code=201)
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
