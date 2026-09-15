"""Projects, apps and the registry behind them: what the platform manages."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.models.base import KEY, SHORT, Base, now
from app.core.db.models.organizations import Organization


class Project(Base):
    __tablename__ = "project"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(SHORT, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    team_id: Mapped[Optional[str]] = mapped_column(KEY)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    organization: Mapped[Organization] = relationship(foreign_keys=[organization_id])


class App(Base):
    __tablename__ = "app"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    registry_id: Mapped[str] = mapped_column(SHORT, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source_host_id: Mapped[Optional[str]] = mapped_column(KEY)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    project: Mapped[Project] = relationship(foreign_keys=[project_id])


class RegistryEntry(Base):
    __tablename__ = "registry"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    default_branch: Mapped[str] = mapped_column(
        SHORT, nullable=False, default="", server_default=""
    )
    branch: Mapped[str] = mapped_column(
        SHORT, nullable=False, default="", server_default=""
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )


class Draft(Base):
    """A file changed on an app through the API and not committed yet: the pending edit lives here, not in a clone, so any instance or worker can apply it."""

    __tablename__ = "draft"

    registry_id: Mapped[str] = mapped_column(KEY, primary_key=True)
    path: Mapped[str] = mapped_column(Text, primary_key=True)
    content: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
