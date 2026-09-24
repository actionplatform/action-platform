"""The dependencies as parameter types, so a route declares what it needs and nothing else."""

from typing import Annotated, Optional

from fastapi import Depends, Header
from sqlalchemy.orm import Session as DbSession

from app.api.dependencies.access import get_caller, org_of
from app.api.dependencies.services import (
    get_app_service,
    get_auth,
    get_commits,
    get_configuration,
    get_db,
    get_host_providers,
    get_integrations,
    get_organization_repository,
    get_projects_repository,
    get_flow,
    get_git_state,
    get_snapshot,
    get_deployments,
    get_ci,
    get_deployment_records,
    get_releases,
    get_import_gateway,
    get_projects,
    get_project_view,
    get_plugins,
    get_queue,
    get_state_signer,
)
from app.services.auth.service import AuthService
from app.core.db.models import Organization
from app.services.access.caller import Caller
from app.services.projects.apps import AppService
from app.repositories.organization import OrganizationRepository
from app.repositories.projects import ProjectsRepository
from app.services.integrations.hosts.directory import IntegrationsDirectory
from app.services.integrations.hosts import HostProviders, OAuthState
from app.services.jobs import JobQueue
from app.services.integrations.plugins import PluginManager
from app.services.projects.organization_import import ImportGateway
from app.services.projects.service import ProjectService
from app.services.projects.view import ProjectView
from app.services.configuration.commit import CommitService
from app.services.configuration.service import ConfigurationService
from app.services.activity.flow import FlowService
from app.services.ci import CiService
from app.services.deployments import DeploymentRecords, DeploymentsService
from app.services.releases import ReleasesService
from app.services.workspace.snapshot import SnapshotService
from app.services.workspace.state import GitStateService

CallerDep = Annotated[Caller, Depends(get_caller)]
DbDep = Annotated[DbSession, Depends(get_db)]
OrganizationRepoDep = Annotated[
    OrganizationRepository, Depends(get_organization_repository)
]
ProjectsRepoDep = Annotated[ProjectsRepository, Depends(get_projects_repository)]
IntegrationsDep = Annotated[IntegrationsDirectory, Depends(get_integrations)]
HostProvidersDep = Annotated[HostProviders, Depends(get_host_providers)]
AuthDep = Annotated[AuthService, Depends(get_auth)]
QueueDep = Annotated[JobQueue, Depends(get_queue)]
PluginsDep = Annotated[PluginManager, Depends(get_plugins)]
SignerDep = Annotated[OAuthState, Depends(get_state_signer)]
AppsDep = Annotated[AppService, Depends(get_app_service)]
ProjectsDep = Annotated[ProjectService, Depends(get_projects)]
ProjectViewDep = Annotated[ProjectView, Depends(get_project_view)]
ImportsDep = Annotated[ImportGateway, Depends(get_import_gateway)]
SnapshotDep = Annotated[SnapshotService, Depends(get_snapshot)]
GitStateDep = Annotated[GitStateService, Depends(get_git_state)]
ReleasesDep = Annotated[ReleasesService, Depends(get_releases)]
DeploymentsDep = Annotated[DeploymentsService, Depends(get_deployments)]
CiDep = Annotated[CiService, Depends(get_ci)]
DeploymentRecordsDep = Annotated[DeploymentRecords, Depends(get_deployment_records)]
FlowDep = Annotated[FlowService, Depends(get_flow)]
ConfigurationDep = Annotated[ConfigurationService, Depends(get_configuration)]
CommitsDep = Annotated[CommitService, Depends(get_commits)]
OrganizationHeader = Annotated[Optional[str], Header(alias="X-Organization")]


def current_org(
    caller: CallerDep, x_organization: OrganizationHeader = None
) -> Organization:
    return org_of(caller, x_organization)


OrgDep = Annotated[Organization, Depends(current_org)]
