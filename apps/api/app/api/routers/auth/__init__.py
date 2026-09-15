"""Routes under /api/auth: sessions, organizations, invitations, the device flow, API tokens."""

from fastapi import APIRouter

from app.api.routers.auth import device, invitations, organizations, sessions, tokens

router = APIRouter()

for part in (sessions, organizations, invitations, device, tokens):
    router.include_router(part.router)

__all__ = ["router"]
