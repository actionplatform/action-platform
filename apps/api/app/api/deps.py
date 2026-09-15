"""FastAPI dependencies: the request's database session and the services built on the registry."""

from typing import Iterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.repositories.registry import Registry
from app.repositories.source import get_registry
from app.services.apps import AppService
from app.services.workspace.configuration import ConfigurationService
from app.services.workspace.flow import FlowService
from app.services.workspace.state import GitStateService
from app.services.workspace.lifecycle import LifecycleService


def get_app_service(registry: Registry = Depends(get_registry)) -> AppService:
    return AppService(registry)


def get_git_state(registry: Registry = Depends(get_registry)) -> GitStateService:
    return GitStateService(registry)


def get_lifecycle(registry: Registry = Depends(get_registry)) -> LifecycleService:
    return LifecycleService(registry)


def get_db(request: Request) -> Iterator[Session]:
    database = request.app.state.db

    if database is None:
        raise HTTPException(503, "no database configured: set AP_DATABASE_URL")

    with database.session() as session:
        yield session


def get_flow(registry: Registry = Depends(get_registry)) -> FlowService:
    return FlowService(registry)


def get_configuration(
    registry: Registry = Depends(get_registry),
) -> ConfigurationService:
    return ConfigurationService(registry)
