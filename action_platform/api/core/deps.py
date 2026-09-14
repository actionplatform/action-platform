from functools import lru_cache
from typing import Iterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from action_platform.api.repositories.registry import DbStore, Registry
from action_platform.api.services.apps import AppService
from action_platform.api.services.configuration import ConfigurationService
from action_platform.api.services.flow import FlowService
from action_platform.api.services.git_state import GitStateService
from action_platform.api.services.lifecycle import LifecycleService


_database = None


def configure_registry(database) -> None:
    global _database
    _database = database
    get_registry.cache_clear()


@lru_cache
def get_registry() -> Registry:
    return Registry(store=DbStore(_database) if _database is not None else None)


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
