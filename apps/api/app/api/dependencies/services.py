"""FastAPI dependencies that build a service for the request."""

from typing import Iterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as DbSession

from app.core.auth.service import AuthService
from app.repositories.registry import Registry
from app.repositories.source import get_registry
from app.services.apps import AppService
from app.services.directory import DirectoryService, DirectoryWrites
from app.services.hosts import OAuthState
from app.services.jobs import JobQueue
from app.services.projects import ProjectService
from app.services.workspace.configuration import ConfigurationService
from app.services.workspace.flow import FlowService
from app.services.workspace.lifecycle import LifecycleService
from app.services.workspace.state import GitStateService


def get_db(request: Request) -> Iterator[DbSession]:
    database = request.app.state.db

    if database is None:
        raise HTTPException(503, "no database configured: set AP_DATABASE_URL")

    with database.session() as session:
        yield session


def get_directory(db: DbSession = Depends(get_db)) -> DirectoryService:
    return DirectoryService(db)


def get_writes(request: Request, db: DbSession = Depends(get_db)) -> DirectoryWrites:
    return DirectoryWrites(db, request.app.state.sealer)


def get_auth(
    request: Request, db: DbSession = Depends(get_db)
) -> Iterator[AuthService]:
    secrets = request.app.state.secrets

    if secrets is None:
        raise HTTPException(503, "auth is not configured: set AP_AUTH_SECRET")

    yield AuthService(db, secrets, request.app.state.verification_uri)


def get_queue(request: Request) -> JobQueue:
    if request.app.state.db is None:
        raise HTTPException(503, "no database configured: set AP_DATABASE_URL")

    return JobQueue(request.app.state.db)


def get_state_signer(request: Request) -> OAuthState:
    return OAuthState(request.app.state.secrets)


def get_app_service(registry: Registry = Depends(get_registry)) -> AppService:
    return AppService(registry)


def get_git_state(registry: Registry = Depends(get_registry)) -> GitStateService:
    return GitStateService(registry)


def get_lifecycle(registry: Registry = Depends(get_registry)) -> LifecycleService:
    return LifecycleService(registry)


def get_flow(registry: Registry = Depends(get_registry)) -> FlowService:
    return FlowService(registry)


def get_configuration(
    registry: Registry = Depends(get_registry),
) -> ConfigurationService:
    return ConfigurationService(registry)


def get_projects(
    writes: DirectoryWrites = Depends(get_writes),
    apps: AppService = Depends(get_app_service),
) -> ProjectService:
    return ProjectService(writes, apps)
