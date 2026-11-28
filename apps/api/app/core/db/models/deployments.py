"""Deployments: a release arriving at one of the app's targets, whoever executed it."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.models.base import KEY, SHORT, Base, now
from app.core.db.models.projects import App

DEPLOYMENT_STATUSES = (
    "queued",
    "running",
    "success",
    "failure",
    "verified",
    "paused",
    "awaiting_approval",
    "rolling_back",
    "rolled_back",
    "aborted",
)
STEP_STATUSES = (
    "pending",
    "running",
    "waiting",
    "succeeded",
    "failed",
    "skipped",
    "cancelled",
)


class Deployment(Base):
    __tablename__ = "deployment"
    __table_args__ = (
        UniqueConstraint("app_id", "target", "executor", "external_ref"),
        Index("ix_deployment_app_started", "app_id", "started_at"),
        Index("ix_deployment_release", "release_id"),
    )

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    app_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("app.id", ondelete="CASCADE"), nullable=False
    )
    target: Mapped[str] = mapped_column(SHORT, nullable=False)
    kind: Mapped[str] = mapped_column(SHORT, nullable=False)
    stage: Mapped[Optional[str]] = mapped_column(SHORT)
    version: Mapped[str] = mapped_column(SHORT, nullable=False)
    release_id: Mapped[Optional[str]] = mapped_column(
        KEY, ForeignKey("release.id", ondelete="SET NULL")
    )
    sha: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(SHORT, nullable=False)
    executor: Mapped[str] = mapped_column(SHORT, nullable=False)
    external_ref: Mapped[str] = mapped_column(SHORT, nullable=False)
    job_id: Mapped[Optional[str]] = mapped_column(KEY)
    ci_run_id: Mapped[Optional[str]] = mapped_column(KEY)
    url: Mapped[Optional[str]] = mapped_column(Text)
    actor: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    strategy: Mapped[str] = mapped_column(
        SHORT, nullable=False, default="recreate", server_default="recreate"
    )
    strategy_config: Mapped[Optional[str]] = mapped_column(Text)
    safety: Mapped[Optional[str]] = mapped_column(Text)
    operations: Mapped[Optional[str]] = mapped_column(Text)
    app: Mapped[App] = relationship(foreign_keys=[app_id])


class DeploymentStep(Base):
    """One step of a deployment's plan, stored when the deployment starts and advanced by the `deploy_step` job."""

    __tablename__ = "deployment_step"
    __table_args__ = (
        UniqueConstraint("deployment_id", "position"),
        Index("ix_deployment_step_deployment", "deployment_id", "position"),
    )

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    deployment_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("deployment.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(SHORT, nullable=False)
    params: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}", server_default="{}"
    )
    status: Mapped[str] = mapped_column(
        SHORT, nullable=False, default="pending", server_default="pending"
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    not_before: Mapped[Optional[datetime]] = mapped_column(DateTime)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    result: Mapped[Optional[str]] = mapped_column(Text)


class DeploymentEvent(Base):
    """What happened to a deployment and who did it: a step that failed, an approval, a pause, an abort."""

    __tablename__ = "deployment_event"
    __table_args__ = (Index("ix_deployment_event_app_at", "app_id", "at"),)

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    deployment_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("deployment.id", ondelete="CASCADE"), nullable=False
    )
    app_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("app.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(SHORT, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text)
    actor: Mapped[Optional[str]] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
