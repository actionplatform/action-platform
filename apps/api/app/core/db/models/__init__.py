"""Every table the API owns, one module per context; `TABLES` is the creation order."""

from app.core.db.models.base import KEY, SHORT, Base, now
from app.core.db.models.auth import User, Session, Account, Verification, DeviceCode
from app.core.db.models.organizations import (
    Organization,
    Member,
    Invitation,
    Team,
    TeamMember,
    OrganizationSetting,
)
from app.core.db.models.projects import Project, App, RegistryEntry, Draft
from app.core.db.models.hosts import SourceHost, OAuthApp, TemplateSource
from app.core.db.models.activity import Release, PullRequest
from app.core.db.models.tokens import ApiToken, ApiTokenClient
from app.core.db.models.jobs import Job

TABLES = list(Base.metadata.sorted_tables)

__all__ = [
    "Account",
    "ApiToken",
    "ApiTokenClient",
    "App",
    "Base",
    "DeviceCode",
    "Draft",
    "Invitation",
    "Job",
    "KEY",
    "Member",
    "OAuthApp",
    "Organization",
    "OrganizationSetting",
    "Project",
    "PullRequest",
    "RegistryEntry",
    "Release",
    "SHORT",
    "Session",
    "SourceHost",
    "TABLES",
    "Team",
    "TeamMember",
    "TemplateSource",
    "User",
    "Verification",
    "now",
]
