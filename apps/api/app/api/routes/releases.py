"""App › Releases: cut a release, preview the next version."""

from typing import Optional

from fastapi import APIRouter

from app.schemas import actions as schemas
from app.api.dependencies import (
    LifecycleDep,
)

router = APIRouter(prefix="/api/apps", tags=["releases"])


@router.post("/{id}/release")
def app_release(
    id: str,
    body: schemas.ReleaseRequest,
    lifecycle: LifecycleDep,
) -> schemas.ReleasePreview:
    return lifecycle.release(id, body)


@router.get("/{id}/next-version")
def app_next_version(
    id: str,
    lifecycle: LifecycleDep,
    level: str = "patch",
    branch: Optional[str] = None,
    component: Optional[str] = None,
) -> schemas.NextVersion:
    return lifecycle.next_version(id, level, branch, component)
