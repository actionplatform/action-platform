"""App › Releases: cut a release, preview the next version."""

from typing import Optional

from fastapi import APIRouter

from app.schemas import releases as schemas
from app.api.dependencies import (
    ReleasesDep,
)

router = APIRouter(prefix="/api/apps", tags=["releases"])


@router.post("/{id}/release")
def app_release(
    id: str,
    body: schemas.ReleaseRequest,
    releases: ReleasesDep,
) -> schemas.ReleasePreview:
    return releases.release(id, body)


@router.get("/{id}/next-version")
def app_next_version(
    id: str,
    releases: ReleasesDep,
    level: str = "patch",
    branch: Optional[str] = None,
    component: Optional[str] = None,
) -> schemas.NextVersion:
    return releases.next_version(id, level, branch, component)
