"""Releases — the platform's own table, one row per tag whatever source named it — and pull requests imported from the code host."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
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


class Release(Base):
    __tablename__ = "release"
    __table_args__ = (
        UniqueConstraint("app_id", "tag"),
        Index("ix_release_app_published", "app_id", "published_at"),
    )

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    app_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("app.id", ondelete="CASCADE"), nullable=False
    )
    tag: Mapped[str] = mapped_column(SHORT, nullable=False)
    component: Mapped[str] = mapped_column(
        SHORT, nullable=False, default="", server_default=""
    )
    version: Mapped[str] = mapped_column(
        SHORT, nullable=False, default="", server_default=""
    )
    name: Mapped[Optional[str]] = mapped_column(Text)
    body: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(Text)
    author: Mapped[Optional[str]] = mapped_column(Text)
    sha: Mapped[Optional[str]] = mapped_column(Text)
    prerelease: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(SHORT, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    app: Mapped[App] = relationship(foreign_keys=[app_id])


class PullRequest(Base):
    __tablename__ = "pull_request"
    __table_args__ = (Index("ix_pull_request_app_updated", "app_id", "updated_at"),)

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    app_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("app.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(Text)
    head: Mapped[str] = mapped_column(Text, nullable=False)
    base: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(SHORT, nullable=False)
    draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    merged_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(SHORT, nullable=False)
    app: Mapped[App] = relationship(foreign_keys=[app_id])
