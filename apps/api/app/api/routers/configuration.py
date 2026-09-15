from typing import Optional

from fastapi import APIRouter, Depends

from app import schemas
from app.api.deps import get_configuration
from app.services.workspace.configuration import ConfigurationService

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
    return config.set_cloud(id, body.target, body.source)


@router.post("/{id}/services", status_code=201)
def add_service(
    id: str,
    body: schemas.ServiceRequest,
    config: ConfigurationService = Depends(get_configuration),
) -> dict:
    return config.add_service(id, body.name, body.provider, body.source)


@router.get("/{id}/changes")
def changes(
    id: str, config: ConfigurationService = Depends(get_configuration)
) -> schemas.Changes:
    return config.changes(id)


@router.post("/{id}/install", status_code=201)
def install_platform(
    id: str,
    body: Optional[schemas.InstallSpec] = None,
    config: ConfigurationService = Depends(get_configuration),
) -> schemas.Installed:
    spec = body or schemas.InstallSpec()

    return config.install_platform(id, spec.type, spec.language, spec.ci)


@router.post("/{id}/discard")
def discard(
    id: str, config: ConfigurationService = Depends(get_configuration)
) -> schemas.Changes:
    return config.discard(id)


@router.post("/{id}/commit", status_code=201)
def commit(
    id: str,
    body: schemas.CommitRequest,
    config: ConfigurationService = Depends(get_configuration),
) -> schemas.CommitResult:
    return config.commit(id, body)
