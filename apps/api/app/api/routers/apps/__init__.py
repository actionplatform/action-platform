"""One app's clone: git state, releases and deploys, git-flow, configuration."""

from fastapi import APIRouter

from app.api.routers.apps import configuration, flow, lifecycle, state

router = APIRouter()

for part in (
    state,
    lifecycle,
    flow,
    configuration,
):
    router.include_router(part.router)

__all__ = ["router"]
