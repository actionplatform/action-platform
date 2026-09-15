"""An organization as its members see it: who they are, members and teams, invitations, settings, template sources."""

from fastapi import APIRouter

from app.api.routers.organizations import (
    identity,
    members,
    invitations,
    settings,
    template_sources,
)

router = APIRouter()

for part in (
    identity,
    members,
    invitations,
    settings,
    template_sources,
):
    router.include_router(part.router)

__all__ = ["router"]
