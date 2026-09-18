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
    SnapshotDep,
)

router = APIRouter(prefix="/api/apps", tags=["configuration"])


@router.get("/{id}/manifest")
def read_manifest(
    id: str,
    snapshot: SnapshotDep,
) -> AppConfigBody:
    return snapshot.manifest(id)


@router.put("/{id}/manifest")
def write_manifest(
    id: str,
    body: AppConfigBody,
    config: ConfigurationDep,
    snapshot: SnapshotDep,
) -> AppConfigBody:
    result = config.write_manifest(id, body.content)
    snapshot.take(id)

    return result


@router.post("/{id}/manifest/export")
def export_manifest(
    id: str,
    config: ConfigurationDep,
    snapshot: SnapshotDep,
) -> AppConfigBody:
    result = config.export_manifest(id)
    snapshot.take(id)

    return result


@router.post("/{id}/cloud")
def set_cloud(
    id: str,
    body: CloudRequest,
    config: ConfigurationDep,
    snapshot: SnapshotDep,
) -> dict:
    result = config.set_cloud(id, body.target, body.source)
    snapshot.take(id)

    return result


@router.post("/{id}/services", status_code=201)
def add_service(
    id: str,
    body: ServiceRequest,
    config: ConfigurationDep,
    snapshot: SnapshotDep,
) -> dict:
    result = config.add_service(id, body.name, body.provider, body.source)
    snapshot.take(id)

    return result


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
    snapshot: SnapshotDep,
    body: Optional[InstallSpec] = None,
) -> Installed:
    spec = body or InstallSpec()

    result = config.install_platform(id, spec.type, spec.language, spec.ci)
    snapshot.take(id)

    return result


@router.post("/{id}/discard")
def discard(
    id: str,
    config: ConfigurationDep,
    snapshot: SnapshotDep,
) -> Changes:
    result = config.discard(id)
    snapshot.take(id)

    return result


@router.post("/{id}/commit", status_code=201)
def commit(
    id: str,
    body: CommitRequest,
    commits: CommitsDep,
) -> CommitResult:
    return commits.commit(id, body)
