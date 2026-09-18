"""Organizations, their members, invitations, teams and settings."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.models.auth import User
from app.core.db.models.base import KEY, SHORT, Base, now


class Organization(Base):
    __tablename__ = "organization"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(SHORT, nullable=False, unique=True)
    logo: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    metadata_: Mapped[Optional[str]] = mapped_column("metadata", Text)


class Member(Base):
    __tablename__ = "member"
    __table_args__ = (
        Index("ix_member_user", "user_id"),
        Index("ix_member_org", "organization_id"),
    )

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(SHORT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    organization: Mapped[Organization] = relationship(foreign_keys=[organization_id])
    user: Mapped[User] = relationship(foreign_keys=[user_id])


class Invitation(Base):
    __tablename__ = "invitation"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(SHORT, nullable=False)
    role: Mapped[Optional[str]] = mapped_column(SHORT)
    status: Mapped[str] = mapped_column(SHORT, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    inviter_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    organization: Mapped[Organization] = relationship(foreign_keys=[organization_id])
    inviter: Mapped[User] = relationship(foreign_keys=[inviter_id])


class Team(Base):
    __tablename__ = "team"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(SHORT, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    organization: Mapped[Organization] = relationship(foreign_keys=[organization_id])


class TeamMember(Base):
    __tablename__ = "team_member"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    team_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("team.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    team: Mapped[Team] = relationship(foreign_keys=[team_id])
    user: Mapped[User] = relationship(foreign_keys=[user_id])


class OrganizationSetting(Base):
    __tablename__ = "organization_setting"

    organization_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("organization.id", ondelete="CASCADE"), primary_key=True
    )
    git_author_name: Mapped[str] = mapped_column(Text, nullable=False)
    git_author_email: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    organization: Mapped[Organization] = relationship(foreign_keys=[organization_id])


class ApiToken(Base):
    __tablename__ = "api_token"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[Optional[str]] = mapped_column(
        KEY, ForeignKey("organization.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(SHORT, nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(KEY)
    app_id: Mapped[Optional[str]] = mapped_column(KEY)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    organization: Mapped[Optional[Organization]] = relationship(
        foreign_keys=[organization_id]
    )


class ApiTokenClient(Base):
    __tablename__ = "api_token_client"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    token_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("api_token.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(SHORT, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    token: Mapped[ApiToken] = relationship(foreign_keys=[token_id])
