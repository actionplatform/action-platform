"""Code hosts connected to an organization, the OAuth apps that connect them, custom template sources."""

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


class SourceHost(Base):
    __tablename__ = "source_host"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(SHORT, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(Text)
    username: Mapped[Optional[str]] = mapped_column(Text)
    token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    default_owner: Mapped[Optional[str]] = mapped_column(Text)
    auth_kind: Mapped[str] = mapped_column(
        SHORT, nullable=False, default="token", server_default="token"
    )
    login: Mapped[Optional[str]] = mapped_column(Text)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    organization: Mapped[Organization] = relationship(foreign_keys=[organization_id])


class OAuthApp(Base):
    __tablename__ = "oauth_app"

    provider: Mapped[str] = mapped_column(SHORT, primary_key=True)
    client_id: Mapped[str] = mapped_column(Text, nullable=False)
    client_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(Text)
    slug: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )


class TemplateSource(Base):
    __tablename__ = "template_source"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    ref: Mapped[str] = mapped_column(
        SHORT, nullable=False, default="main", server_default="main"
    )
    source_host_id: Mapped[Optional[str]] = mapped_column(KEY)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    organization: Mapped[Organization] = relationship(foreign_keys=[organization_id])
