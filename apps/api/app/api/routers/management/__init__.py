"""Routes under /api/v1 for the directory of an organization: identity and tokens, projects and apps, teams and members, invitations, hosts, OAuth, settings, template sources, imports, jobs."""

from fastapi import APIRouter

from app.api.routers.management import (
    apps,
    github_app,
    hosts,
    identity,
    invitations,
    jobs,
    oauth_apps,
    oauth_flow,
    organization_import,
    projects,
    settings,
    teams,
    template_sources,
)

router = APIRouter()

for part in (
    identity,
    projects,
    apps,
    teams,
    invitations,
    hosts,
    oauth_apps,
    oauth_flow,
    github_app,
    settings,
    template_sources,
    organization_import,
    jobs,
):
    router.include_router(part.router)

__all__ = ["router"]
