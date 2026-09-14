"""GitHub specifics: App manifests, installations and what an installation may do."""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import quote

from action_platform.api.services.shared.credentials import Credentials
from action_platform.api.services.shared.http import get_json, post_form
from action_platform.core.exception import ProviderError
from action_platform.api.services.hosts.access import _get, _owner
from action_platform.api.services.hosts.providers import GITHUB_MANIFEST_PERMISSIONS


def installation_owner(access_token: str, installation_id: str) -> Optional[str]:
    try:
        data = get_json(
            "https://api.github.com/user/installations",
            {
                "authorization": f"Bearer {access_token}",
                "accept": "application/vnd.github+json",
            },
        )
    except ProviderError:
        return None

    return next(
        (
            i["account"]["login"]
            for i in data.get("installations", [])
            if str(i.get("id")) == installation_id
        ),
        None,
    )


def github_manifest(origin: str, host: str, return_to: str) -> dict[str, Any]:
    return {
        "name": f"Action Platform ({host})"[:34],
        "url": origin,
        "redirect_url": f"{origin}/api/oauth/github/manifest/callback",
        "callback_urls": [f"{origin}/api/oauth/github/callback"],
        "setup_url": f"{origin}{return_to}",
        "public": True,
        "request_oauth_on_install": True,
        "default_permissions": GITHUB_MANIFEST_PERMISSIONS,
    }


def convert_github_manifest(code: str) -> dict[str, Any]:
    data = post_form(
        f"https://api.github.com/app-manifests/{quote(code, safe='')}/conversions",
        {},
        {"accept": "application/vnd.github+json", "x-github-api-version": "2022-11-28"},
    )

    if not data.get("client_id") or not data.get("client_secret"):
        raise ProviderError("GitHub app creation failed")

    return data


def _github_access(creds: Credentials, app_slug: Optional[str]) -> dict[str, Any]:
    api = (creds.base_url or "").rstrip("/") or "https://api.github.com"
    headers = {
        "authorization": f"Bearer {creds.token}",
        "x-github-api-version": "2022-11-28",
    }
    status, me = _get(f"{api}/user", headers)

    if not me:
        return {
            "ok": False,
            "error": f"token rejected by GitHub ({status}); reconnect the host",
        }

    status, listing = _get(f"{api}/user/installations", headers)
    install_url = (
        f"https://github.com/apps/{app_slug}/installations/select_target"
        if app_slug
        else None
    )

    if status in (403, 404):
        return {
            "ok": True,
            "kind": "github",
            "login": me["login"],
            "installations": [],
            "installUrl": install_url,
            "problems": [
                "This token is not from a GitHub App (personal token): repositories are created with the token's own scopes. Needs `repo` and `workflow`."
            ],
        }

    installations = []

    for i in (listing or {}).get("installations", []):
        org = i["account"].get("type") == "Organization"
        selected = None

        if i.get("repository_selection") != "all":
            _, repos = _get(
                f"{api}/user/installations/{i['id']}/repositories?per_page=100", headers
            )
            selected = [r["full_name"] for r in (repos or {}).get("repositories", [])]

        installations.append(
            _owner(
                i["account"]["login"],
                "org" if org else "user",
                "all" if i.get("repository_selection") == "all" else "selected",
                (i.get("permissions") or {}).get("administration", "none"),
                (i.get("permissions") or {}).get("contents", "none"),
                selected=selected,
                configure_url=f"https://github.com/organizations/{i['account']['login']}/settings/installations/{i['id']}"
                if org
                else f"https://github.com/settings/installations/{i['id']}",
            )
        )

    problems = []

    if not installations:
        problems.append(
            f"The GitHub App is not installed on any account this token can see. Install it on {me['login']} (or the organization that owns the repositories) with access to all repositories."
        )

    for i in installations:
        if i["administration"] != "write":
            problems.append(
                f'{i["account"]}: repository permission "Administration" is {i["administration"]}; it must be "Read and write" to create repositories. Change it in the app\'s Permissions & events, then accept the new permissions on the installation.'
            )

        if i["contents"] != "write":
            problems.append(
                f'{i["account"]}: repository permission "Contents" is {i["contents"]}; it must be "Read and write" to push.'
            )

        if i["repositories"] != "all":
            problems.append(
                f"{i['account']}: installed on selected repositories only; new repositories created by the platform will not be reachable. Switch the installation to all repositories."
            )

    return {
        "ok": True,
        "kind": "github",
        "login": me["login"],
        "installations": installations,
        "installUrl": install_url,
        "problems": problems,
    }
