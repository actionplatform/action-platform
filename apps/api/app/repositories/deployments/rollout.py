"""The plan of a deployment as rows: its steps in order, the events, and the deployments that still hold their scope."""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session as DbSession

from app.core.db.models import Deployment, DeploymentEvent, DeploymentStep
from app.core.shared.clock import now

ACTIVE_STEP = ("pending", "running", "waiting")
DONE_STEP = ("succeeded", "failed", "skipped", "cancelled")
HELD = ("running", "paused", "awaiting_approval", "rolling_back")


def loads(raw: Optional[str], default: Any = None) -> Any:
    if not raw:
        return default

    try:
        return json.loads(raw)
    except ValueError:
        return default


def dumps(value: Any) -> str:
    return json.dumps(value, default=str)


class RolloutStore:
    def __init__(self, db: DbSession) -> None:
        self.db = db

    def deployment(self, id: str, app_id: Optional[str] = None) -> Optional[Deployment]:
        row = self.db.get(Deployment, id)

        if row is None or (app_id is not None and row.app_id != app_id):
            return None

        return row

    def steps(self, deployment_id: str) -> list[DeploymentStep]:
        return list(
            self.db.scalars(
                select(DeploymentStep)
                .where(DeploymentStep.deployment_id == deployment_id)
                .order_by(DeploymentStep.position)
            )
        )

    def current(self, deployment_id: str) -> Optional[DeploymentStep]:
        return self.db.scalar(
            select(DeploymentStep)
            .where(
                DeploymentStep.deployment_id == deployment_id,
                DeploymentStep.status.in_(ACTIVE_STEP),
            )
            .order_by(DeploymentStep.position)
            .limit(1)
        )

    def plan(
        self, deployment: Deployment, steps: list[dict[str, Any]]
    ) -> list[DeploymentStep]:
        rows = [
            DeploymentStep(
                id=str(uuid.uuid4()),
                deployment_id=deployment.id,
                position=position,
                kind=step["kind"],
                params=dumps(step.get("params") or {}),
                status="pending",
                attempts=0,
            )
            for position, step in enumerate(steps)
        ]
        self.db.add_all(rows)
        self.db.flush()

        return rows

    def append(
        self, deployment_id: str, kind: str, params: dict[str, Any]
    ) -> DeploymentStep:
        last = self.db.scalar(
            select(func.max(DeploymentStep.position)).where(
                DeploymentStep.deployment_id == deployment_id
            )
        )
        row = DeploymentStep(
            id=str(uuid.uuid4()),
            deployment_id=deployment_id,
            position=(last if last is not None else -1) + 1,
            kind=kind,
            params=dumps(params),
            status="pending",
            attempts=0,
        )
        self.db.add(row)
        self.db.flush()

        return row

    def cancel_pending(self, deployment_id: str) -> None:
        moment = now()

        for step in self.steps(deployment_id):
            if step.status in ("pending", "waiting"):
                step.status = "cancelled"
                step.finished_at = moment

    def held(self, app_id: str, stage: str) -> Optional[Deployment]:
        """A deployment of the app run step by step that still holds `stage`: running, paused, waiting for approval or rolling back."""
        return self.db.scalar(
            select(Deployment)
            .where(
                Deployment.app_id == app_id,
                Deployment.stage == stage,
                Deployment.status.in_(HELD),
                exists().where(DeploymentStep.deployment_id == Deployment.id),
            )
            .limit(1)
        )

    def event(
        self,
        deployment: Deployment,
        kind: str,
        title: str,
        detail: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> DeploymentEvent:
        row = DeploymentEvent(
            id=str(uuid.uuid4()),
            deployment_id=deployment.id,
            app_id=deployment.app_id,
            kind=kind,
            title=title,
            detail=detail,
            actor=actor,
            at=now(),
        )
        self.db.add(row)
        self.db.flush()

        return row

    def events(self, deployment_id: str) -> list[DeploymentEvent]:
        return list(
            self.db.scalars(
                select(DeploymentEvent)
                .where(DeploymentEvent.deployment_id == deployment_id)
                .order_by(DeploymentEvent.at)
            )
        )
