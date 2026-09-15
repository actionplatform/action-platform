"""Code hosts: one HostProvider per kind (OAuth, API bases, access checks), the signed OAuth state, and the registry that picks one by kind."""

from action_platform_api.services.hosts.access import AccessReport, Owner, Probe
from action_platform_api.services.hosts.bitbucket import BitbucketProvider
from action_platform_api.services.hosts.github import (
    MANIFEST_PERMISSIONS,
    GithubProvider,
)
from action_platform_api.services.hosts.gitlab import GitlabProvider
from action_platform_api.services.hosts.registry import PROVIDERS, HostProviders
from action_platform_api.services.hosts.state import STATE_TTL, OAuthState
from action_platform_api.services.hosts.tokens import TokenResponse

__all__ = [
    "MANIFEST_PERMISSIONS",
    "PROVIDERS",
    "STATE_TTL",
    "AccessReport",
    "BitbucketProvider",
    "GithubProvider",
    "GitlabProvider",
    "HostProviders",
    "OAuthState",
    "Owner",
    "Probe",
    "TokenResponse",
]
