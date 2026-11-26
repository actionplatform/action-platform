from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.schemas.common import UtcDateTime


class DeployRequest(BaseModel):
    stage: Optional[str] = None
    scope: Optional[str] = None
    dry_run: bool = True
    version: Optional[str] = None
    force: bool = False


class DeployResult(BaseModel):
    target: str
    ok: bool
    version: str
    url: Optional[str] = None
    error: Optional[str] = None


class Diagnosis(BaseModel):
    ok: bool
    target: str
    status: str = ""
    version: Optional[str] = None
    url: Optional[str] = None
    details: dict[str, str] = {}


class TargetRow(BaseModel):
    name: str
    kind: str
    run_by: str
    stages: list[str] = []
    workflow: Optional[str] = None
    job: Optional[str] = None


class DeploymentRow(BaseModel):
    id: str
    target: str
    kind: str
    stage: Optional[str] = None
    version: str
    release_id: Optional[str] = None
    sha: Optional[str] = None
    status: str
    executor: str
    job_id: Optional[str] = None
    ci_run_id: Optional[str] = None
    url: Optional[str] = None
    actor: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[UtcDateTime] = None
    finished_at: Optional[UtcDateTime] = None
    verified_at: Optional[UtcDateTime] = None
    synced_at: UtcDateTime


class Deployments(BaseModel):
    targets: list[TargetRow]
    deployments: list[DeploymentRow]
    error: Optional[str] = None


class RecordDeploymentRequest(BaseModel):
    target: str
    version: str
    stage: Optional[str] = None
    url: Optional[str] = None
    sha: Optional[str] = None
    ok: bool = True
