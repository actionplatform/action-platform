"""What plugins remember on the hosted platform — one row per (plugin, key), the options table."""

from datetime import datetime

from sqlalchemy import DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.models.base import SHORT, Base, now


class PluginOption(Base):
    __tablename__ = "plugin_option"

    plugin: Mapped[str] = mapped_column(SHORT, primary_key=True)
    key: Mapped[str] = mapped_column(SHORT, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="null")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, onupdate=now
    )
