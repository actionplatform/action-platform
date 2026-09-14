"""What each code host is called, which scopes its OAuth flow asks for, and where its API and web UI live."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from action_platform.api.services.shared.credentials import OAuthApp

PROVIDER_INFO = {
    "github": {
        "label": "GitHub",
        "scopes": "repo workflow read:org delete_repo",
        "callback_hint": "GitHub → Settings → Developer settings → OAuth Apps",
    },
    "gitlab": {
        "label": "GitLab",
        "scopes": "api write_repository read_user",
        "callback_hint": "GitLab → User settings → Applications (or group/instance applications)",
    },
    "bitbucket": {
        "label": "Bitbucket",
        "scopes": "",
        "callback_hint": "Bitbucket → Workspace settings → OAuth consumers (permissions: account, repositories write/admin/delete, pull requests write)",
    },
}

GITHUB_MANIFEST_PERMISSIONS = {
    "administration": "write",
    "contents": "write",
    "workflows": "write",
    "pull_requests": "write",
    "metadata": "read",
    "members": "read",
}


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def base_of(provider: str, app: OAuthApp) -> str:
    if provider == "github":
        return re.sub(
            r"/api/v3$", "", (app.base_url or "https://github.com").rstrip("/")
        )

    if provider == "gitlab":
        return (app.base_url or "https://gitlab.com").rstrip("/")

    return "https://bitbucket.org"


def api_base_of(provider: str, app: OAuthApp) -> str:
    if provider == "github":
        return (
            f"{base_of(provider, app)}/api/v3"
            if app.base_url
            else "https://api.github.com"
        )

    if provider == "gitlab":
        return f"{base_of(provider, app)}/api/v4"

    return "https://api.bitbucket.org/2.0"


def stored_base_url(provider: str, app: OAuthApp) -> Optional[str]:
    if not app.base_url:
        return None

    if provider == "github":
        return api_base_of(provider, app)

    if provider == "gitlab":
        return base_of(provider, app)

    return None
