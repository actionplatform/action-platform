"""Code hosts: what a token can reach, and the OAuth dance that connects one."""

import base64
import hmac
import json
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import quote, urlencode

from action_platform.api.auth.secrets import Secrets
from action_platform.api.services.directory import Credentials, OAuthApp
from action_platform.api.services.http import basic, get_json, post_form
from action_platform.core.exception import ProviderError

PROVIDER_INFO = {
    "github": {
        "label": "GitHub",
        "scopes": "repo workflow read:org",
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
        "callback_hint": "Bitbucket → Workspace settings → OAuth consumers (permissions: account, repositories write/admin, pull requests write)",
    },
}
STATE_TTL = 10 * 60
GITHUB_MANIFEST_PERMISSIONS = {
    "administration": "write",
    "contents": "write",
    "workflows": "write",
    "pull_requests": "write",
    "metadata": "read",
}


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


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


class OAuthState:
    """Signed, short-lived state for the OAuth round trip: organization, where to return, who started it."""

    def __init__(self, secrets: Secrets) -> None:
        self.key = secrets.subkey("oauth-state")

    def sign(self, organization_id: str, return_to: str, user_id: Optional[str]) -> str:
        payload = _b64(
            json.dumps(
                {
                    "orgId": organization_id,
                    "returnTo": return_to,
                    "userId": user_id,
                    "nonce": secrets.token_hex(8),
                    "ts": int(time.time() * 1000),
                },
                separators=(",", ":"),
            ).encode()
        )

        return f"{payload}.{self._mac(payload)}"

    def verify(
        self, raw: Optional[str], user_id: Optional[str]
    ) -> Optional[dict[str, Any]]:
        if not raw or "." not in raw:
            return None

        payload, _, mac = raw.rpartition(".")

        if not hmac.compare_digest(mac, self._mac(payload)):
            return None

        try:
            state = json.loads(_unb64(payload))
        except ValueError:
            return None

        if time.time() * 1000 - state.get("ts", 0) > STATE_TTL * 1000:
            return None

        if state.get("userId") and state["userId"] != user_id:
            return None

        return state

    def _mac(self, payload: str) -> str:
        return _b64(hmac.new(self.key, payload.encode(), "sha256").digest())


def callback_url(provider: str, origin: str) -> str:
    return f"{origin}/api/oauth/{provider}/callback"


def authorize_url(provider: str, app: OAuthApp, origin: str, state: str) -> str:
    params = {
        "client_id": app.client_id,
        "redirect_uri": callback_url(provider, origin),
        "state": state,
        "response_type": "code",
    }

    if PROVIDER_INFO[provider]["scopes"]:
        params["scope"] = PROVIDER_INFO[provider]["scopes"]

    if provider == "github":
        return f"{base_of(provider, app)}/login/oauth/authorize?{urlencode(params)}"

    if provider == "gitlab":
        return f"{base_of(provider, app)}/oauth/authorize?{urlencode(params)}"

    return f"https://bitbucket.org/site/oauth2/authorize?{urlencode(params)}"


def _token(data: dict[str, Any]) -> tuple[str, Optional[str], Optional[datetime]]:
    access = data.get("access_token")

    if not isinstance(access, str) or not access:
        raise ProviderError(
            str(
                data.get("error_description")
                or data.get("error")
                or "no access token in the provider's response"
            )
        )

    expires_in = data.get("expires_in")
    refresh = data.get("refresh_token")

    return (
        access,
        refresh if isinstance(refresh, str) else None,
        now() + timedelta(seconds=int(expires_in))
        if isinstance(expires_in, (int, float))
        else None,
    )


def exchange_code(
    provider: str, app: OAuthApp, origin: str, code: str
) -> tuple[str, Optional[str], Optional[datetime]]:
    redirect = callback_url(provider, origin)

    if provider == "github":
        return _token(
            post_form(
                f"{base_of(provider, app)}/login/oauth/access_token",
                {
                    "client_id": app.client_id,
                    "client_secret": app.client_secret,
                    "code": code,
                    "redirect_uri": redirect,
                },
            )
        )

    if provider == "gitlab":
        return _token(
            post_form(
                f"{base_of(provider, app)}/oauth/token",
                {
                    "client_id": app.client_id,
                    "client_secret": app.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect,
                },
            )
        )

    return _token(
        post_form(
            "https://bitbucket.org/site/oauth2/access_token",
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect,
            },
            {"authorization": basic(app.client_id, app.client_secret)},
        )
    )


def identity(
    provider: str, app: OAuthApp, access_token: str
) -> tuple[str, Optional[str]]:
    user = get_json(
        f"{api_base_of(provider, app)}/user",
        {"authorization": f"Bearer {access_token}"},
    )
    login = user.get("login") if provider == "github" else user.get("username")

    if not login:
        raise ProviderError(
            f"{PROVIDER_INFO[provider]['label']}: could not read the signed-in user"
        )

    return login, user.get("name") or user.get("display_name")


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


def _get(url: str, headers: dict[str, str]) -> tuple[int, Any]:
    try:
        return 200, get_json(url, headers)
    except ProviderError as e:
        digits = re.match(r"(\d{3}) from", str(e))

        return (int(digits.group(1)) if digits else 0), None


def host_access(creds: Credentials, github_app_slug: Optional[str]) -> dict[str, Any]:
    """What the connected account may create with: accounts, installations or workspaces, with what is wrong about each."""

    if creds.kind == "github":
        return _github_access(creds, github_app_slug)

    if creds.kind == "gitlab":
        return _gitlab_access(creds)

    if creds.kind == "bitbucket":
        return _bitbucket_access(creds)

    return {"ok": False, "error": f"no access check for {creds.kind}"}


def _owner(
    account: str,
    kind: str,
    repositories: str,
    administration: str,
    contents: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "account": account,
        "kind": kind,
        "repositories": repositories,
        "administration": administration,
        "contents": contents,
        "canCreateRepos": administration == "write" and contents == "write",
        "selected": extra.get("selected"),
        "configureUrl": extra.get("configure_url"),
    }


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
