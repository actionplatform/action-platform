"""Projects, the apps registered in them, and importing a whole organization from a host."""

from fastapi import APIRouter

from app.api.routers.projects import apps, organization_import, projects

router = APIRouter()

for part in (
    projects,
    apps,
    organization_import,
):
    router.include_router(part.router)

__all__ = ["router"]
