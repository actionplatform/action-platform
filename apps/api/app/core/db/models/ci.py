"""CI: the servers an organization connected and the runs imported for each app."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.models.base import KEY, SHORT, Base, now
from app.core.db.models.organization import Organization
from app.core.db.models.projects import App


class CiHost(Base):
    __tablename__ = "ci_host"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(SHORT, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(Text)
    token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    organization: Mapped[Organization] = relationship(foreign_keys=[organization_id])


class CiRun(Base):
    __tablename__ = "ci_run"
    __table_args__ = (UniqueConstraint("app_id", "source", "number"),)

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    app_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("app.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(SHORT, nullable=False)
    number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(SHORT, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(Text)
    branch: Mapped[Optional[str]] = mapped_column(Text)
    sha: Mapped[Optional[str]] = mapped_column(Text)
    trigger: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    app: Mapped[App] = relationship(foreign_keys=[app_id])
