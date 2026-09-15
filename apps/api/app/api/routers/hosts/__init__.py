"""Code hosts: connections, OAuth apps, the OAuth flow, GitHub Apps."""

from fastapi import APIRouter

from app.api.routers.hosts import connections, github_app, oauth_apps, oauth_flow

router = APIRouter()

for part in (
    connections,
    oauth_apps,
    oauth_flow,
    github_app,
):
    router.include_router(part.router)

__all__ = ["router"]
