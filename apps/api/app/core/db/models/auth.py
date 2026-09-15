"""Accounts: users, sessions, linked accounts, verification codes, device codes."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.models.base import KEY, SHORT, Base, now


class User(Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(SHORT, nullable=False, unique=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    image: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )


class Session(Base):
    __tablename__ = "session"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    token: Mapped[str] = mapped_column(SHORT, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    ip_address: Mapped[Optional[str]] = mapped_column(Text)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    user_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    active_organization_id: Mapped[Optional[str]] = mapped_column(KEY)
    user: Mapped[User] = relationship(foreign_keys=[user_id])


class Account(Base):
    __tablename__ = "account"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    account_id: Mapped[str] = mapped_column(SHORT, nullable=False)
    provider_id: Mapped[str] = mapped_column(SHORT, nullable=False)
    user_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    access_token: Mapped[Optional[str]] = mapped_column(Text)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    id_token: Mapped[Optional[str]] = mapped_column(Text)
    access_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    refresh_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    scope: Mapped[Optional[str]] = mapped_column(Text)
    password: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    user: Mapped[User] = relationship(foreign_keys=[user_id])


class Verification(Base):
    __tablename__ = "verification"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    identifier: Mapped[str] = mapped_column(SHORT, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=now, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=now, server_default=func.now()
    )


class DeviceCode(Base):
    __tablename__ = "device_code"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    device_code: Mapped[str] = mapped_column(SHORT, nullable=False)
    user_code: Mapped[str] = mapped_column(SHORT, nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(KEY)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(SHORT, nullable=False)
    last_polled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    polling_interval: Mapped[Optional[int]] = mapped_column(Integer)
    client_id: Mapped[Optional[str]] = mapped_column(SHORT)
    scope: Mapped[Optional[str]] = mapped_column(Text)
