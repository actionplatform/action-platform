"""What platform.toml holds, kept by the platform — one row per registered app; the file in the repository is a mirror written on request."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.models.base import KEY, Base, now


class AppConfig(Base):
    __tablename__ = "app_config"

    registry_id: Mapped[str] = mapped_column(KEY, primary_key=True)
    data: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, onupdate=now
    )


class AppSnapshot(Base):
    __tablename__ = "app_snapshot"

    registry_id: Mapped[str] = mapped_column(KEY, primary_key=True)
    data: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    taken_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, onupdate=now
    )
