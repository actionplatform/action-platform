"""Code hosts: one HostProvider per kind (OAuth, API bases, access checks), the signed OAuth state, and the registry that picks one by kind."""

from app.services.hosts.access import AccessReport, Owner, Probe
from app.services.hosts.bitbucket import BitbucketProvider
from app.services.hosts.connect import HostConnector
from app.services.hosts.github import (
    MANIFEST_PERMISSIONS,
    GithubProvider,
)
from app.services.hosts.gitlab import GitlabProvider
from app.services.hosts.registry import PROVIDERS, HostProviders
from app.services.hosts.state import STATE_TTL, OAuthState
from app.services.hosts.tokens import TokenResponse

__all__ = [
    "MANIFEST_PERMISSIONS",
    "PROVIDERS",
    "STATE_TTL",
    "AccessReport",
    "BitbucketProvider",
    "GithubProvider",
    "GitlabProvider",
    "HostConnector",
    "HostProviders",
    "OAuthState",
    "Owner",
    "Probe",
    "TokenResponse",
]
