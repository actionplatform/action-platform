"""Queued work for the worker."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.models.base import KEY, SHORT, Base, now


class Job(Base):
    __tablename__ = "job"
    __table_args__ = (
        UniqueConstraint("kind", "app_id", "dedupe_key", name="uq_job_dedupe"),
    )

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    kind: Mapped[str] = mapped_column(SHORT, nullable=False)
    status: Mapped[str] = mapped_column(
        SHORT, nullable=False, default="queued", server_default="queued"
    )
    organization_id: Mapped[Optional[str]] = mapped_column(KEY)
    app_id: Mapped[Optional[str]] = mapped_column(KEY)
    dedupe_key: Mapped[Optional[str]] = mapped_column(SHORT)
    payload: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}", server_default="{}"
    )
    result: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    run_after: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    locked_by: Mapped[Optional[str]] = mapped_column(SHORT)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
