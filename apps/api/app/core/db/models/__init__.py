"""Every table the API owns, one module per context; `TABLES` is the creation order."""

from app.core.db.models.activity import PullRequest, Release, ReleaseReadiness
from app.core.db.models.auth import Account, DeviceCode, Session, User, Verification
from app.core.db.models.base import KEY, SHORT, Base, now
from app.core.db.models.ci import CiHost, CiRun
from app.core.db.models.configuration import AppConfig, AppSnapshot
from app.core.db.models.deployments import Deployment
from app.core.db.models.integrations import (
    OAuthApp,
    PluginOption,
    SigningKey,
    SourceHost,
    TemplateSource,
)
from app.core.db.models.jobs import Job
from app.core.db.models.organization import (
    ApiToken,
    ApiTokenClient,
    Invitation,
    Member,
    Organization,
    OrganizationSetting,
    Team,
    TeamMember,
)
from app.core.db.models.projects import App, Draft, Project, RegistryEntry

__all__ = [
    "Account",
    "ApiToken",
    "ApiTokenClient",
    "App",
    "AppConfig",
    "AppSnapshot",
    "CiHost",
    "CiRun",
    "Deployment",
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
    "PluginOption",
    "Project",
    "PullRequest",
    "RegistryEntry",
    "Release",
    "ReleaseReadiness",
    "SHORT",
    "Session",
    "SigningKey",
    "SourceHost",
    "TABLES",
    "Team",
    "TeamMember",
    "TemplateSource",
    "User",
    "Verification",
    "now",
]
