"""Deployments: a release arriving at one of the app's targets, whoever executed it."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.models.base import KEY, SHORT, Base, now
from app.core.db.models.projects import App

DEPLOYMENT_STATUSES = ("queued", "running", "success", "failure", "verified")
EXECUTORS = ("platform", "github_actions", "jenkins", "manual")


class Deployment(Base):
    __tablename__ = "deployment"
    __table_args__ = (UniqueConstraint("app_id", "target", "executor", "external_ref"),)

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
    app: Mapped[App] = relationship(foreign_keys=[app_id])
