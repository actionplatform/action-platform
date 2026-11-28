from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, field_validator

from app.schemas.common import UtcDateTime


class DeployRequest(BaseModel):
    stage: Optional[str] = None
    scope: Optional[str] = None
    dry_run: bool = True
    version: Optional[str] = None
    force: bool = False
    strategy: Optional[str] = None
    strategy_config: Optional[dict[str, Any]] = None
    safety: Optional[dict[str, Any]] = None


def _json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return None

    return value


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
    strategy: str = "recreate"
    strategy_config: Optional[dict[str, Any]] = None
    safety: Optional[dict[str, Any]] = None
    operations: Optional[list[str]] = None

    @field_validator("strategy_config", "safety", "operations", mode="before")
    @classmethod
    def _decoded(cls, value: Any) -> Any:
        return _json(value)

    @field_validator("strategy", mode="before")
    @classmethod
    def _recreate(cls, value: Any) -> Any:
        return value or "recreate"


class Deployments(BaseModel):
    targets: list[TargetRow]
    deployments: list[DeploymentRow]
    error: Optional[str] = None


class DeploymentsPage(Deployments):
    total: int
    page: int
    per: int


class RecordDeploymentRequest(BaseModel):
    target: str
    version: str
    stage: Optional[str] = None
    url: Optional[str] = None
    sha: Optional[str] = None
    ok: bool = True


class StrategyRow(BaseModel):
    id: str
    label: str
    description: str
    config_schema: dict[str, Any]
    needs: list[str]


class DeployStrategies(BaseModel):
    strategies: list[StrategyRow]
    safety_schema: dict[str, Any]


class ScopeStrategy(BaseModel):
    id: str
    supported: bool
    native: bool = False
    missing: list[str] = []
    reason: Optional[str] = None


class StepRow(BaseModel):
    id: str
    position: int
    kind: str
    params: dict[str, Any] = {}
    status: str
    attempts: int = 0
    not_before: Optional[UtcDateTime] = None
    started_at: Optional[UtcDateTime] = None
    finished_at: Optional[UtcDateTime] = None
    result: Optional[dict[str, Any]] = None

    @field_validator("params", "result", mode="before")
    @classmethod
    def _decoded(cls, value: Any) -> Any:
        return _json(value)


class DeploymentEventRow(BaseModel):
    id: str
    kind: str
    title: str
    detail: Optional[str] = None
    actor: Optional[str] = None
    at: UtcDateTime


class DeploymentControl(BaseModel):
    deployment: DeploymentRow
    steps: list[StepRow]
    queued: bool = False
    live: Optional[str] = None
