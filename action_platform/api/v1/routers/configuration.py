from fastapi import APIRouter, Depends

from action_platform.api import schemas
from action_platform.api.core.deps import get_configuration
from action_platform.api.services.configuration import ConfigurationService

router = APIRouter(prefix="/apps", tags=["configuration"])


@router.get("/{id}/manifest")
def read_manifest(
    id: str, config: ConfigurationService = Depends(get_configuration)
) -> schemas.ManifestBody:
    return config.manifest(id)


@router.put("/{id}/manifest")
def write_manifest(
    id: str,
    body: schemas.ManifestBody,
    config: ConfigurationService = Depends(get_configuration),
) -> schemas.ManifestBody:
    return config.write_manifest(id, body.content)


@router.post("/{id}/cloud")
def set_cloud(
    id: str,
    body: schemas.CloudRequest,
    config: ConfigurationService = Depends(get_configuration),
) -> dict:
    return config.set_cloud(id, body.target)


@router.post("/{id}/services", status_code=201)
def add_service(
    id: str,
    body: schemas.ServiceRequest,
    config: ConfigurationService = Depends(get_configuration),
) -> dict:
    return config.add_service(id, body.name, body.provider)


@router.post("/{id}/commit", status_code=201)
def commit(
    id: str,
    body: schemas.CommitRequest,
    config: ConfigurationService = Depends(get_configuration),
) -> schemas.CommitResult:
    return config.commit(id, body)
