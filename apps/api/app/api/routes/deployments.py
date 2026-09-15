"""App › Deployments: deploy a release, diagnose what is live."""

from typing import Optional

from fastapi import APIRouter

from app.api.dependencies import LifecycleDep
from app.schemas import actions as schemas

router = APIRouter(prefix="/api/apps", tags=["deployments"])


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
