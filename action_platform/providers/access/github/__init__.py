"""GitHub access: members, teams and repository permissions of an organization, and read-only checks of its repositories."""

from action_platform.providers.access.github.checks import Org
from action_platform.providers.access.github.client import API_URL, client
from action_platform.providers.access.github.models import (
    BranchProtection,
    OrgSettings,
    RepoProtection,
    RepoSettings,
)
from action_platform.providers.access.github.provider import (
    PERMISSIONS,
    SCOPES,
    GitHubProvider,
)

__all__ = [
    "API_URL",
    "PERMISSIONS",
    "SCOPES",
    "BranchProtection",
    "GitHubProvider",
    "Org",
    "OrgSettings",
    "RepoProtection",
    "RepoSettings",
    "client",
]
