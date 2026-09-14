"""Code hosts: OAuth connection, GitHub App manifests, and what a connected account may do."""

from typing import Any, Optional

from action_platform.api.services.credentials import Credentials
from action_platform.api.services.hosts.bitbucket import (
    _bitbucket_access,
    first_workspace,
)
from action_platform.api.services.hosts.github import (
    _github_access,
    convert_github_manifest,
    github_manifest,
    installation_owner,
)
from action_platform.api.services.hosts.gitlab import _gitlab_access
from action_platform.api.services.hosts.oauth import (
    STATE_TTL,
    OAuthState,
    authorize_url,
    callback_url,
    exchange_code,
    identity,
)
from action_platform.api.services.hosts.providers import (
    GITHUB_MANIFEST_PERMISSIONS,
    PROVIDER_INFO,
    api_base_of,
    base_of,
    now,
    stored_base_url,
)


def host_access(creds: Credentials, github_app_slug: Optional[str]) -> dict[str, Any]:
    """What the connected account may create with: accounts, installations or workspaces, with what is wrong about each."""

    if creds.kind == "github":
        return _github_access(creds, github_app_slug)

    if creds.kind == "gitlab":
        return _gitlab_access(creds)

    if creds.kind == "bitbucket":
        return _bitbucket_access(creds)

    return {"ok": False, "error": f"no access check for {creds.kind}"}


__all__ = [
    "GITHUB_MANIFEST_PERMISSIONS",
    "PROVIDER_INFO",
    "STATE_TTL",
    "OAuthState",
    "api_base_of",
    "authorize_url",
    "base_of",
    "callback_url",
    "convert_github_manifest",
    "exchange_code",
    "first_workspace",
    "github_manifest",
    "host_access",
    "identity",
    "installation_owner",
    "now",
    "stored_base_url",
]
