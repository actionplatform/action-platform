"""Every route the API serves, one package per domain."""

from fastapi import APIRouter

from app.api.routers import apps, auth, catalog, hosts, jobs, organizations, projects

router = APIRouter()

for part in (auth, organizations, hosts, projects, apps, catalog, jobs):
    router.include_router(part.router)

__all__ = ["router"]
