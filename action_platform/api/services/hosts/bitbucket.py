"""Bitbucket specifics: workspaces and their permissions."""

from __future__ import annotations

from typing import Any, Optional

from action_platform.api.services.credentials import Credentials
from action_platform.api.services.http import basic, get_json
from action_platform.core.exception import ProviderError
from action_platform.api.services.hosts.access import _get, _owner


def first_workspace(access_token: str) -> Optional[str]:
    try:
        data = get_json(
            "https://api.bitbucket.org/2.0/user/permissions/workspaces?pagelen=100",
            {"authorization": f"Bearer {access_token}"},
        )
    except ProviderError:
        return None

    spaces = data.get("values", [])
    chosen = (
        next((w for w in spaces if w.get("permission") == "owner"), None)
        or next((w for w in spaces if w.get("permission") == "collaborator"), None)
        or (spaces[0] if spaces else None)
    )

    return chosen["workspace"]["slug"] if chosen else None


def _bitbucket_access(creds: Credentials) -> dict[str, Any]:
    auth = (
        basic(creds.username, creds.token)
        if creds.username
        else f"Bearer {creds.token}"
    )
    headers = {"authorization": auth}
    status, me = _get("https://api.bitbucket.org/2.0/user", headers)

    if not me:
        return {
            "ok": False,
            "error": f"token rejected by Bitbucket ({status}); reconnect the host",
        }

    spaces_status, spaces = _get(
        "https://api.bitbucket.org/2.0/user/permissions/workspaces?pagelen=100", headers
    )
    installations = [
        _owner(
            w["workspace"]["slug"],
            "org",
            "all",
            "write" if w.get("permission") in ("owner", "collaborator") else "none",
            "write",
        )
        for w in (spaces or {}).get("values", [])
    ]

    if not installations:
        _, member = _get(
            "https://api.bitbucket.org/2.0/workspaces?role=member&pagelen=100", headers
        )
        installations = [
            _owner(w["slug"], "org", "all", "write", "write")
            for w in (member or {}).get("values", [])
        ]

    problems = []

    if not installations:
        problems.append(
            f"Bitbucket lists no workspace for this account (permissions endpoint answered {spaces_status}). The OAuth consumer needs Workspace membership: Read and Account: Read; repositories are created inside a workspace, never under the account name."
        )

    return {
        "ok": True,
        "kind": "bitbucket",
        "login": me["username"],
        "installations": installations,
        "installUrl": None,
        "problems": problems,
    }
