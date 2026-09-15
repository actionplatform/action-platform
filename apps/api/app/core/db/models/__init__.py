"""Every table the API owns, one module per context; `TABLES` is the creation order."""

from app.core.db.models.activity import PullRequest, Release
from app.core.db.models.auth import Account, DeviceCode, Session, User, Verification
from app.core.db.models.base import KEY, SHORT, Base, now
from app.core.db.models.hosts import OAuthApp, SourceHost, TemplateSource
from app.core.db.models.jobs import Job
from app.core.db.models.organizations import (
    Invitation,
    Member,
    Organization,
    OrganizationSetting,
    Team,
    TeamMember,
)
from app.core.db.models.plugins import PluginOption
from app.core.db.models.projects import App, Draft, Project, RegistryEntry
from app.core.db.models.tokens import ApiToken, ApiTokenClient

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
    "PluginOption",
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
