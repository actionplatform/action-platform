"""The key the platform signs identity tokens with — one RSA pair, made on first use, the private half sealed."""

from datetime import datetime

from sqlalchemy import DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.models.base import SHORT, Base, now


class SigningKey(Base):
    __tablename__ = "signing_key"

    kid: Mapped[str] = mapped_column(SHORT, primary_key=True)
    private_sealed: Mapped[str] = mapped_column(Text, nullable=False)
    public_pem: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now)
