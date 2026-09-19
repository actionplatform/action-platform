"""Where an app's releases are deployed: one row per scope, with its kind and its criticality."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.models.base import KEY, SHORT, Base, now
from app.core.db.models.projects import App


class Scope(Base):
    __tablename__ = "scope"
    __table_args__ = (UniqueConstraint("app_id", "name", name="uq_scope_app_name"),)

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    app_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("app.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(SHORT, nullable=False)
    kind: Mapped[str] = mapped_column(SHORT, nullable=False, default="web")
    criticality: Mapped[str] = mapped_column(SHORT, nullable=False, default="low")
    created_by: Mapped[Optional[str]] = mapped_column(KEY)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    app: Mapped[App] = relationship(foreign_keys=[app_id])
