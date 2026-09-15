from typing import Optional

from fastapi import APIRouter, Depends

from app import schemas
from app.api.dependencies import get_app_service, get_git_state
from app.services.apps import AppService
from app.services.workspace.state import GitStateService

router = APIRouter(prefix="/apps", tags=["apps"])


@router.get("")
def list_apps(apps: AppService = Depends(get_app_service)) -> list[schemas.AppRow]:
    return apps.list()


@router.post("", status_code=201)
def add_app(
    body: schemas.AddAppRequest, apps: AppService = Depends(get_app_service)
) -> schemas.AppEntry:
    return apps.add(body.url, body.name, body.credentials, body.install)


@router.post("/init", status_code=201)
def init_app(
    body: schemas.InitRequest, apps: AppService = Depends(get_app_service)
) -> schemas.InitResult:
    return apps.init(body)


@router.get("/{id}")
def app_detail(
    id: str, apps: AppService = Depends(get_app_service)
) -> schemas.AppDetail:
    return apps.detail(id)


@router.delete("/{id}", status_code=204)
def remove_app(id: str, apps: AppService = Depends(get_app_service)) -> None:
    apps.remove(id)


@router.post("/{id}/sync")
def sync_app(
    id: str,
    body: Optional[schemas.SyncRequest] = None,
    apps: AppService = Depends(get_app_service),
) -> schemas.AppEntry:
    return apps.sync(
        id, body.credentials if body else None, reset=bool(body and body.reset)
    )


@router.post("/{id}/push")
def push_app(
    id: str, body: schemas.PushRequest, apps: AppService = Depends(get_app_service)
) -> schemas.PushResult:
    return apps.push(id, body)


@router.get("/{id}/gitflow")
def app_gitflow(
    id: str, state: GitStateService = Depends(get_git_state)
) -> schemas.GitflowReport:
    return state.gitflow(id)


@router.get("/{id}/commits")
def app_commits(
    id: str, limit: int = 20, state: GitStateService = Depends(get_git_state)
) -> list[schemas.Commit]:
    return state.commits(id, limit)


@router.get("/{id}/tags")
def app_tags(id: str, state: GitStateService = Depends(get_git_state)) -> list[str]:
    return state.tags(id)


@router.get("/{id}/releases")
def app_releases(
    id: str, state: GitStateService = Depends(get_git_state)
) -> list[schemas.Release]:
    return state.releases(id)


@router.get("/{id}/branches")
def app_branches(
    id: str, state: GitStateService = Depends(get_git_state)
) -> list[schemas.Branch]:
    return state.branches(id)
