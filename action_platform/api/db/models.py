from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

KEY = String(36)
SHORT = String(255)


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


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


class Release(Base):
    __tablename__ = "release"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    app_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("app.id", ondelete="CASCADE"), nullable=False
    )
    tag: Mapped[str] = mapped_column(SHORT, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(Text)
    body: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(Text)
    author: Mapped[Optional[str]] = mapped_column(Text)
    sha: Mapped[Optional[str]] = mapped_column(Text)
    prerelease: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(SHORT, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    app: Mapped[App] = relationship(foreign_keys=[app_id])


class PullRequest(Base):
    __tablename__ = "pull_request"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    app_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("app.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(Text)
    head: Mapped[str] = mapped_column(Text, nullable=False)
    base: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(SHORT, nullable=False)
    draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    merged_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(SHORT, nullable=False)
    app: Mapped[App] = relationship(foreign_keys=[app_id])


class TemplateSource(Base):
    __tablename__ = "template_source"

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        KEY, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    ref: Mapped[str] = mapped_column(
        SHORT, nullable=False, default="v1", server_default="v1"
    )
    source_host_id: Mapped[Optional[str]] = mapped_column(KEY)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    organization: Mapped[Organization] = relationship(foreign_keys=[organization_id])


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )


class Job(Base):
    __tablename__ = "job"
    __table_args__ = (
        UniqueConstraint("kind", "app_id", "dedupe_key", name="uq_job_dedupe"),
    )

    id: Mapped[str] = mapped_column(KEY, primary_key=True)
    kind: Mapped[str] = mapped_column(SHORT, nullable=False)
    status: Mapped[str] = mapped_column(
        SHORT, nullable=False, default="queued", server_default="queued"
    )
    organization_id: Mapped[Optional[str]] = mapped_column(KEY)
    app_id: Mapped[Optional[str]] = mapped_column(KEY)
    dedupe_key: Mapped[Optional[str]] = mapped_column(SHORT)
    payload: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}", server_default="{}"
    )
    result: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    run_after: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    locked_by: Mapped[Optional[str]] = mapped_column(SHORT)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now, server_default=func.now()
    )


TABLES = list(Base.metadata.sorted_tables)
