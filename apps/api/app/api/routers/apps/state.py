from typing import Optional

from fastapi import APIRouter, Request

from app import schemas
from app.api.dependencies import (
    AppsDep,
    GitStateDep,
)

router = APIRouter(prefix="/api/apps", tags=["apps"])


@router.get("")
def list_apps(
    request: Request,
    apps: AppsDep,
) -> list[schemas.AppRow]:
    """Every app, or only those within the caller's reach when the gate said which."""
    return apps.list(only=getattr(request.state, "allowed_registry_ids", None))


@router.post("", status_code=201)
def add_app(
    body: schemas.AddAppRequest,
    apps: AppsDep,
) -> schemas.AppEntry:
    return apps.add(body.url, body.name, body.credentials, body.install)


@router.post("/init", status_code=201)
def init_app(
    body: schemas.InitRequest,
    apps: AppsDep,
) -> schemas.InitResult:
    return apps.init(body)


@router.get("/{id}")
def app_detail(
    id: str,
    apps: AppsDep,
) -> schemas.AppDetail:
    return apps.detail(id)


@router.delete("/{id}", status_code=204)
def remove_app(
    id: str,
    apps: AppsDep,
) -> None:
    apps.remove(id)


@router.post("/{id}/sync")
def sync_app(
    id: str,
    apps: AppsDep,
    body: Optional[schemas.SyncRequest] = None,
) -> schemas.AppEntry:
    return apps.sync(
        id, body.credentials if body else None, reset=bool(body and body.reset)
    )


@router.post("/{id}/push")
def push_app(
    id: str,
    body: schemas.PushRequest,
    apps: AppsDep,
) -> schemas.PushResult:
    return apps.push(id, body)


@router.get("/{id}/gitflow")
def app_gitflow(
    id: str,
    state: GitStateDep,
) -> schemas.GitflowReport:
    return state.gitflow(id)


@router.get("/{id}/commits")
def app_commits(
    id: str,
    state: GitStateDep,
    limit: int = 20,
) -> list[schemas.Commit]:
    return state.commits(id, limit)


@router.get("/{id}/tags")
def app_tags(
    id: str,
    state: GitStateDep,
) -> list[str]:
    return state.tags(id)


@router.get("/{id}/releases")
def app_releases(
    id: str,
    state: GitStateDep,
) -> list[schemas.Release]:
    return state.releases(id)


@router.get("/{id}/branches")
def app_branches(
    id: str,
    state: GitStateDep,
) -> list[schemas.Branch]:
    return state.branches(id)
