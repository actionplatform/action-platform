"""The dependencies as parameter types, so a route declares what it needs and nothing else."""

from typing import Annotated, Optional

from fastapi import Depends, Header
from sqlalchemy.orm import Session as DbSession

from app.api.dependencies.access import get_caller, org_of
from app.api.dependencies.services import (
    get_app_service,
    get_auth,
    get_configuration,
    get_db,
    get_directory,
    get_flow,
    get_git_state,
    get_lifecycle,
    get_queue,
    get_state_signer,
    get_writes,
)
from app.core.auth.service import AuthService
from app.core.db.models import Organization
from app.services.access.caller import Caller
from app.services.apps import AppService
from app.services.directory import DirectoryService, DirectoryWrites
from app.services.hosts import OAuthState
from app.services.jobs import JobQueue
from app.services.workspace.configuration import ConfigurationService
from app.services.workspace.flow import FlowService
from app.services.workspace.lifecycle import LifecycleService
from app.services.workspace.state import GitStateService

CallerDep = Annotated[Caller, Depends(get_caller)]
DbDep = Annotated[DbSession, Depends(get_db)]
DirectoryDep = Annotated[DirectoryService, Depends(get_directory)]
WritesDep = Annotated[DirectoryWrites, Depends(get_writes)]
AuthDep = Annotated[AuthService, Depends(get_auth)]
QueueDep = Annotated[JobQueue, Depends(get_queue)]
SignerDep = Annotated[OAuthState, Depends(get_state_signer)]
AppsDep = Annotated[AppService, Depends(get_app_service)]
GitStateDep = Annotated[GitStateService, Depends(get_git_state)]
LifecycleDep = Annotated[LifecycleService, Depends(get_lifecycle)]
FlowDep = Annotated[FlowService, Depends(get_flow)]
ConfigurationDep = Annotated[ConfigurationService, Depends(get_configuration)]
OrganizationHeader = Annotated[Optional[str], Header(alias="X-Organization")]


def current_org(
    caller: CallerDep, x_organization: OrganizationHeader = None
) -> Organization:
    return org_of(caller, x_organization)


OrgDep = Annotated[Organization, Depends(current_org)]
