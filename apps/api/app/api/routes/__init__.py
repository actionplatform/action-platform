"""Every route the API serves — one file per context, mirroring the menu; routers are mounted in this order."""

from fastapi import APIRouter

from app.api.routes import (
    activity,
    apps,
    configuration,
    deployments,
    identity,
    jobs,
    releases,
    templates,
)
from app.api.routes.auth import device, invitations as invites, sessions, setup
from app.api.routes.integrations import (
    ci_hosts,
    github_app,
    hosts,
    oauth_apps,
    oauth_flow,
    plugins,
    template_sources,
)
from app.api.routes.organization import identity as org_identity
from app.api.routes.organization import (
    invitations,
    members,
    sessions as connected_apps,
    settings,
)
from app.api.routes.projects import apps as project_apps
from app.api.routes.projects import ci as project_ci
from app.api.routes.projects import deployments as project_deployments
from app.api.routes.projects import organization_import, projects

routers = [
    sessions,
    setup,
    invites,
    device,
    connected_apps,
    org_identity,
    members,
    invitations,
    settings,
    template_sources,
    hosts,
    ci_hosts,
    oauth_apps,
    oauth_flow,
    github_app,
    projects,
    project_apps,
    project_ci,
    project_deployments,
    organization_import,
    apps,
    releases,
    deployments,
    activity,
    configuration,
    templates,
    jobs,
    plugins,
    identity,
]

router = APIRouter()

for part in routers:
    router.include_router(part.router)

__all__ = ["router", "routers"]
