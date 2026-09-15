"""Workspace routes under /api (and /api/v1 through the gate): apps and their git state, releases and deploys, git-flow, configuration, the templates catalog."""

from fastapi import APIRouter

from app.api.routers.workspace import actions, apps, catalog, configuration, flow

router = APIRouter(prefix="/api")

for part in (catalog, apps, actions, flow, configuration):
    router.include_router(part.router)

__all__ = ["router"]
