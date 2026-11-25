"""Git-flow enforced on the code host: what each app's host enforces, what changed it, and the organization's default."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.models.base import KEY, SHORT, Base, now
from app.core.db.models.organization import Organization
from app.core.db.models.projects import App


class AppProtection(Base):
    __tablename__ = "app_protection"

    app_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("app.id", ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    enforced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    app: Mapped[App] = relationship(foreign_keys=[app_id])


class ProtectionEvent(Base):
    __tablename__ = "protection_event"
    __table_args__ = (Index("ix_protection_event_app_at", "app_id", "at"),)

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
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
    app: Mapped[App] = relationship(foreign_keys=[app_id])


class ProtectionDefault(Base):
    __tablename__ = "protection_default"

    organization_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("organization.id", ondelete="CASCADE"), primary_key=True
    )
    enforce: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    organization: Mapped[Organization] = relationship(foreign_keys=[organization_id])
