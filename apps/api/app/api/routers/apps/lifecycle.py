from typing import Optional

from fastapi import APIRouter

from app.schemas import actions as schemas
from app.api.dependencies import (
    LifecycleDep,
)

router = APIRouter(prefix="/api/apps", tags=["actions"])


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


@router.post("/{id}/deploy")
def app_deploy(
    id: str,
    body: schemas.DeployRequest,
    lifecycle: LifecycleDep,
) -> list[schemas.DeployResult]:
    return lifecycle.deploy(id, body)


@router.get("/{id}/diagnose")
def app_diagnose(
    id: str,
    lifecycle: LifecycleDep,
    stage: Optional[str] = None,
) -> list[schemas.Diagnosis]:
    return lifecycle.diagnose(id, stage)
