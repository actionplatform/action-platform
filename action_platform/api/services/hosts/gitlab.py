"""GitLab specifics: the groups the account can create projects in."""

from __future__ import annotations

import re
from typing import Any

from action_platform.api.services.shared.credentials import Credentials
from action_platform.api.services.hosts.access import _get, _owner


def _gitlab_access(creds: Credentials) -> dict[str, Any]:
    api = (
        re.sub(
            r"/api/v4$", "", (creds.base_url or "").rstrip("/") or "https://gitlab.com"
        )
        + "/api/v4"
    )
    headers = {"authorization": f"Bearer {creds.token}"}
    status, me = _get(f"{api}/user", headers)

    if not me:
        return {
            "ok": False,
            "error": f"token rejected by GitLab ({status}); reconnect the host",
        }

    groups_status, groups = _get(
        f"{api}/groups?min_access_level=30&per_page=100&order_by=path", headers
    )
    can_create = me.get("can_create_project") is not False
    installations = [
        _owner(
            me["username"], "user", "all", "write" if can_create else "none", "write"
        )
    ]
    installations += [
        _owner(g["full_path"], "org", "all", "write", "write") for g in (groups or [])
    ]
    problems = []

    if not can_create:
        problems.append(
            f"{me['username']} cannot create projects in the personal namespace; pick a group instead."
        )

    if groups_status != 200:
        problems.append("Could not list groups: the token needs the `api` scope.")

    return {
        "ok": True,
        "kind": "gitlab",
        "login": me["username"],
        "installations": installations,
        "installUrl": None,
        "problems": problems,
    }
