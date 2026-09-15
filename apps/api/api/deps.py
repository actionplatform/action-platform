"""FastAPI dependencies: the request's database session and the services built on the registry."""

from typing import Iterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from action_platform_api.repositories.registry import Registry
from action_platform_api.repositories.source import get_registry
from action_platform_api.services.apps import AppService
from action_platform_api.services.workspace.configuration import ConfigurationService
from action_platform_api.services.workspace.flow import FlowService
from action_platform_api.services.workspace.state import GitStateService
from action_platform_api.services.workspace.lifecycle import LifecycleService


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
