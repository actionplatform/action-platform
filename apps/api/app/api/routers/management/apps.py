"""Apps inside a project: added from a repository or generated, their host, their imported activity."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from action_platform.core.exception import ActionPlatformError
from app.api.dependencies import (
    allowed,
    app_of,
    get_app_service,
    get_caller,
    get_writes,
    imports_of,
    org_of,
    project_of,
)
from app.core.shared.urls import GitUrl
from app.schemas import SourceCredentials
from app.schemas import management as schemas
from app.services.access.caller import Caller
from app.services.access.enrich import credentials_for
from app.services.activity import ActivityService
from app.services.apps import AppService
from app.services.directory import DirectoryWrites


router = APIRouter(prefix="/api/v1", tags=["management"])


@router.post("/projects/{project_id}/apps", status_code=201)
def add_app(
    project_id: str,
    body: schemas.AddAppToProject,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
    apps: AppService = Depends(get_app_service),
) -> schemas.AppAdded:
    org = org_of(caller, x_organization)
    allowed(caller, org, "project.manage")
    project = project_of(writes, org, project_id)
    url = body.url.strip()

    if not url:
        raise HTTPException(400, "url is required")

    host_id = writes.host_id_for_url(org.id, url)
    kind = GitUrl(url).kind

    if kind and host_id is None:
        raise HTTPException(
            400,
            f"No {kind} host is connected to this organization. Connect one in Settings so private repositories can be cloned.",
        )

    credentials = credentials_for(writes, org, None, {"url": url})
    entry = apps.add(url, None, SourceCredentials(**credentials), body.install)
    app = writes.create_app(project.id, entry["id"], entry["name"], host_id)
    ActivityService(writes.db).sync_all(
        app.id, writes.credentials_for(org.id, host_id), GitUrl(url).repo
    )

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
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
    apps: AppService = Depends(get_app_service),
) -> schemas.AppInitialized:
    org = org_of(caller, x_organization)
    allowed(caller, org, "project.manage")
    project = project_of(writes, org, project_id)
    creds = (
        writes.credentials_for(org.id, body.source_host_id)
        if body.source_host_id
        else None
    )

    if body.push and creds is None:
        raise HTTPException(400, "pushing needs a source host")

    name, email = writes.git_author_of(org.id)
    request = body.model_copy(
        update={
            "credentials": SourceCredentials(
                **{
                    **(creds.as_dict() if creds else {}),
                    "author_name": name,
                    "author_email": email,
                }
            ),
            "source": writes.source_spec_by_name(org.id, body.template_source),
        }
    )
    result = apps.init(request)
    app = writes.create_app(
        project.id, result["id"], result["name"], body.source_host_id
    )

    if result.get("pushed") and creds is not None:
        ActivityService(writes.db).sync_all(
            app.id, creds, GitUrl(result.get("url", "")).repo
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
    repository: bool = False,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
    apps: AppService = Depends(get_app_service),
) -> schemas.Removed:
    org = org_of(caller, x_organization)
    allowed(caller, org, "project.manage")
    project = project_of(writes, org, project_id)
    app = writes.app(project.id, app_id)

    if app is None:
        return schemas.Removed()

    deleted = apps.delete_through_host(writes, org.id, app) if repository else None

    try:
        apps.remove(app.registry_id)
    except ActionPlatformError:
        pass

    writes.delete_app(project.id, app_id)

    return schemas.Removed(
        removed=[app.registry_id], repositories=[deleted] if deleted else []
    )


@router.put("/projects/{project_id}/apps/{app_id}/host")
def set_app_host(
    project_id: str,
    app_id: str,
    body: schemas.AppHostRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.AppHostRequest:
    org = org_of(caller, x_organization)
    allowed(caller, org, "app.flow", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    if body.source_host_id and writes.host(org.id, body.source_host_id) is None:
        raise HTTPException(404, "host not found")

    writes.set_app_host(app, body.source_host_id or None)

    return schemas.AppHostRequest(source_host_id=app.source_host_id)


@router.get("/projects/{project_id}/apps/{app_id}/imports")
def imports(
    project_id: str,
    app_id: str,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.Imports:
    org = org_of(caller, x_organization)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    return imports_of(writes.db, app.id)


@router.post("/projects/{project_id}/apps/{app_id}/imports")
def sync_imports(
    project_id: str,
    app_id: str,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
    apps: AppService = Depends(get_app_service),
) -> schemas.Imports:
    org = org_of(caller, x_organization)
    allowed(caller, org, "app.sync", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)
    detail = apps.detail(app.registry_id)
    repo = (
        detail.get("source_host", {}).get("repo") or GitUrl(detail.get("url", "")).repo
    )

    if app.source_host_id is None:
        host_id = writes.host_id_for_url(org.id, detail.get("url", ""))

        if host_id:
            writes.set_app_host(app, host_id)

    errors = ActivityService(writes.db).sync_all(
        app.id, writes.credentials_for(org.id, app.source_host_id), repo
    )

    return imports_of(writes.db, app.id, errors)
