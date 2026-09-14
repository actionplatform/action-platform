from typing import Optional

from fastapi import APIRouter, Depends

from action_platform.api import schemas
from action_platform.api.core.deps import get_lifecycle
from action_platform.api.services.lifecycle import LifecycleService

router = APIRouter(prefix="/apps", tags=["actions"])


@router.post("/{id}/release")
def app_release(
    id: str,
    body: schemas.ReleaseRequest,
    lifecycle: LifecycleService = Depends(get_lifecycle),
) -> schemas.ReleasePreview:
    return lifecycle.release(id, body)


@router.get("/{id}/next-version")
def app_next_version(
    id: str,
    level: str = "patch",
    branch: Optional[str] = None,
    component: Optional[str] = None,
    lifecycle: LifecycleService = Depends(get_lifecycle),
) -> schemas.NextVersion:
    return lifecycle.next_version(id, level, branch, component)


@router.post("/{id}/deploy")
def app_deploy(
    id: str,
    body: schemas.DeployRequest,
    lifecycle: LifecycleService = Depends(get_lifecycle),
) -> list[schemas.DeployResult]:
    return lifecycle.deploy(id, body)


@router.get("/{id}/diagnose")
def app_diagnose(
    id: str,
    stage: Optional[str] = None,
    lifecycle: LifecycleService = Depends(get_lifecycle),
) -> list[schemas.Diagnosis]:
    return lifecycle.diagnose(id, stage)
