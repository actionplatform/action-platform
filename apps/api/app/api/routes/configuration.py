from typing import Optional

from fastapi import APIRouter

from app.schemas.configuration import (
    AppConfigBody,
    Changes,
    CloudRequest,
    CommitRequest,
    CommitResult,
    ServiceRequest,
)
from app.schemas.projects import InstallSpec, Installed
from app.api.dependencies import (
    CommitsDep,
    ConfigurationDep,
)

router = APIRouter(prefix="/api/apps", tags=["configuration"])


@router.get("/{id}/manifest")
def read_manifest(
    id: str,
    config: ConfigurationDep,
) -> AppConfigBody:
    return config.manifest(id)


@router.put("/{id}/manifest")
def write_manifest(
    id: str,
    body: AppConfigBody,
    config: ConfigurationDep,
) -> AppConfigBody:
    return config.write_manifest(id, body.content)


@router.post("/{id}/manifest/export")
def export_manifest(
    id: str,
    config: ConfigurationDep,
) -> AppConfigBody:
    return config.export_manifest(id)


@router.post("/{id}/cloud")
def set_cloud(
    id: str,
    body: CloudRequest,
    config: ConfigurationDep,
) -> dict:
    return config.set_cloud(id, body.target, body.source)


@router.post("/{id}/services", status_code=201)
def add_service(
    id: str,
    body: ServiceRequest,
    config: ConfigurationDep,
) -> dict:
    return config.add_service(id, body.name, body.provider, body.source)


@router.get("/{id}/changes")
def changes(
    id: str,
    config: ConfigurationDep,
) -> Changes:
    return config.changes(id)


@router.post("/{id}/install", status_code=201)
def install_platform(
    id: str,
    config: ConfigurationDep,
    body: Optional[InstallSpec] = None,
) -> Installed:
    spec = body or InstallSpec()

    return config.install_platform(id, spec.type, spec.language, spec.ci)


@router.post("/{id}/discard")
def discard(
    id: str,
    config: ConfigurationDep,
) -> Changes:
    return config.discard(id)


@router.post("/{id}/commit", status_code=201)
def commit(
    id: str,
    body: CommitRequest,
    commits: CommitsDep,
) -> CommitResult:
    return commits.commit(id, body)
