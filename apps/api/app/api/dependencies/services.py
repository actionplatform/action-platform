"""FastAPI dependencies that build a service for the request."""

from typing import Iterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as DbSession

from app.services.auth.service import AuthService
from app.repositories.configuration.config_store import ConfigStore
from app.repositories.workspace.registry import Registry
from app.repositories.workspace.source import get_registry
from app.services.projects.apps import AppService
from app.repositories.organization import OrganizationRepository
from app.repositories.projects import ProjectsRepository
from app.services.integrations.hosts.directory import IntegrationsDirectory
from app.services.projects.organization_import.directory import ImportDirectory
from app.services.integrations.hosts import OAuthState
from app.services.jobs import JobQueue
from app.services.projects.organization_import import ImportGateway
from app.services.integrations.plugins import PluginManager
from app.services.projects.service import ProjectService
from app.services.configuration.commit import CommitService
from app.services.configuration.service import ConfigurationService
from app.services.activity.flow import FlowService
from app.services.deployments import DeploymentsService
from app.services.releases import ReleasesService
from app.services.workspace.state import GitStateService


def get_db(request: Request) -> Iterator[DbSession]:
    database = request.app.state.db

    if database is None:
        raise HTTPException(503, "no database configured: set AP_DATABASE_URL")

    with database.session() as session:
        yield session


def get_organization_repository(
    request: Request, db: DbSession = Depends(get_db)
) -> OrganizationRepository:
    return OrganizationRepository(db, request.app.state.sealer)


def get_projects_repository(
    request: Request, db: DbSession = Depends(get_db)
) -> ProjectsRepository:
    return ProjectsRepository(db, request.app.state.sealer)


def get_integrations(
    request: Request, db: DbSession = Depends(get_db)
) -> IntegrationsDirectory:
    return IntegrationsDirectory(db, request.app.state.sealer)


def get_auth(
    request: Request, db: DbSession = Depends(get_db)
) -> Iterator[AuthService]:
    secrets = request.app.state.secrets

    if secrets is None:
        raise HTTPException(503, "auth is not configured: set AP_AUTH_SECRET")

    yield AuthService(db, secrets, request.app.state.verification_uri)


def get_plugins(request: Request) -> PluginManager:
    if request.app.state.db is None:
        raise HTTPException(503, "no database configured: set AP_DATABASE_URL")

    return PluginManager(request.app.state.db)


def get_queue(request: Request) -> JobQueue:
    if request.app.state.db is None:
        raise HTTPException(503, "no database configured: set AP_DATABASE_URL")

    return JobQueue(request.app.state.db)


def get_state_signer(request: Request) -> OAuthState:
    return OAuthState(request.app.state.secrets)


def get_config_store(registry: Registry = Depends(get_registry)) -> ConfigStore:
    return ConfigStore(registry.store.database)


def get_app_service(
    registry: Registry = Depends(get_registry),
    configs: ConfigStore = Depends(get_config_store),
) -> AppService:
    return AppService(registry, configs)


def get_git_state(registry: Registry = Depends(get_registry)) -> GitStateService:
    return GitStateService(registry)


def get_releases(
    registry: Registry = Depends(get_registry),
    configs: ConfigStore = Depends(get_config_store),
) -> ReleasesService:
    return ReleasesService(registry, configs=configs)


def get_deployments(
    registry: Registry = Depends(get_registry),
    configs: ConfigStore = Depends(get_config_store),
) -> DeploymentsService:
    return DeploymentsService(registry, configs=configs)


def get_flow(
    registry: Registry = Depends(get_registry),
    configs: ConfigStore = Depends(get_config_store),
) -> FlowService:
    return FlowService(registry, configs)


def get_commits(
    registry: Registry = Depends(get_registry),
    configs: ConfigStore = Depends(get_config_store),
) -> CommitService:
    return CommitService(registry, configs)


def get_configuration(
    registry: Registry = Depends(get_registry),
    configs: ConfigStore = Depends(get_config_store),
) -> ConfigurationService:
    return ConfigurationService(registry, configs)


def get_import_directory(
    request: Request, db: DbSession = Depends(get_db)
) -> ImportDirectory:
    return ImportDirectory(db, request.app.state.sealer)


def get_projects(
    writes: ImportDirectory = Depends(get_import_directory),
    apps: AppService = Depends(get_app_service),
) -> ProjectService:
    return ProjectService(writes, apps)


def get_import_gateway(
    writes: ImportDirectory = Depends(get_import_directory),
    queue: JobQueue = Depends(get_queue),
    registry: Registry = Depends(get_registry),
) -> ImportGateway:
    return ImportGateway(writes, registry, queue)
