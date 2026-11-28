"""App › Deployments: deploy a release, diagnose what is live."""

from typing import Optional

from fastapi import APIRouter, Depends

from app.api.dependencies import DeploymentsDep, legacy_surface
from app.schemas import deployments as schemas

router = APIRouter(
    prefix="/api/apps",
    tags=["deployments"],
    deprecated=True,
    dependencies=[Depends(legacy_surface)],
)


@router.post("/{id}/deploy")
def app_deploy(
    id: str,
    body: schemas.DeployRequest,
    deployments: DeploymentsDep,
) -> list[schemas.DeployResult]:
    return deployments.deploy(id, body)


@router.get("/{id}/diagnose")
def app_diagnose(
    id: str,
    deployments: DeploymentsDep,
    stage: Optional[str] = None,
) -> list[schemas.Diagnosis]:
    return deployments.diagnose(id, stage)
