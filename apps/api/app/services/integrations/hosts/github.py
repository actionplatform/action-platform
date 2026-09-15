"""GitHub: OAuth and GitHub Apps, manifests, installations and what an installation may do."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional
from urllib.parse import quote, urlencode

from action_platform.core.exception import ProviderError
from app.core.abc import HostProvider
from app.core.shared.credentials import Credentials, OAuthApp
from app.core.shared.http import http
from app.services.integrations.hosts.access import AccessReport, Owner, Probe
from app.services.integrations.hosts.tokens import TokenResponse

MANIFEST_PERMISSIONS = {
    "administration": "write",
    "contents": "write",
    "workflows": "write",
    "pull_requests": "write",
    "metadata": "read",
    "members": "read",
}
API_VERSION = "2022-11-28"


class GithubProvider(HostProvider):
    kind = "github"
    label = "GitHub"
    scopes = "repo workflow read:org delete_repo"
    callback_hint = "GitHub → Settings → Developer settings → OAuth Apps"

    def web_base(self, app: OAuthApp) -> str:
        return re.sub(
            r"/api/v3$", "", (app.base_url or "https://github.com").rstrip("/")
        )

    def api_base(self, app: OAuthApp) -> str:
        return (
            f"{self.web_base(app)}/api/v3" if app.base_url else "https://api.github.com"
        )

    def stored_base_url(self, app: OAuthApp) -> Optional[str]:
        return self.api_base(app) if app.base_url else None

    def authorize_url(self, app: OAuthApp, origin: str, state: str) -> str:
        params = {
            "client_id": app.client_id,
            "redirect_uri": self.callback_url(origin),
            "state": state,
            "response_type": "code",
            "scope": self.scopes,
        }

        return f"{self.web_base(app)}/login/oauth/authorize?{urlencode(params)}"

    def exchange_code(
        self, app: OAuthApp, origin: str, code: str
    ) -> tuple[str, Optional[str], Optional[datetime]]:
        data = http.post_form(
            f"{self.web_base(app)}/login/oauth/access_token",
            {
                "client_id": app.client_id,
                "client_secret": app.client_secret,
                "code": code,
                "redirect_uri": self.callback_url(origin),
            },
        )

        return TokenResponse(data).read()

    def refresh(
        self, app: OAuthApp, refresh_token: str
    ) -> tuple[str, Optional[str], Optional[datetime]]:
        data = http.post_form(
            f"{self.web_base(app)}/login/oauth/access_token",
            {
                "client_id": app.client_id,
                "client_secret": app.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )

        return TokenResponse(data).read()

    def identity(self, app: OAuthApp, access_token: str) -> tuple[str, Optional[str]]:
        user = http.get_json(
            f"{self.api_base(app)}/user", {"authorization": f"Bearer {access_token}"}
        )

        if not user.get("login"):
            raise ProviderError("GitHub: could not read the signed-in user")

        return user["login"], user.get("name")

    def manifest(self, origin: str, host: str, return_to: str) -> dict[str, Any]:
        """The GitHub App manifest the setup wizard sends to GitHub."""
        return {
            "name": f"Action Platform ({host})"[:34],
            "url": origin,
            "redirect_url": f"{origin}/api/oauth/github/manifest/callback",
            "callback_urls": [self.callback_url(origin)],
            "setup_url": f"{origin}{return_to}",
            "public": True,
            "request_oauth_on_install": True,
            "default_permissions": MANIFEST_PERMISSIONS,
        }

    def convert_manifest(self, code: str) -> dict[str, Any]:
        """Trade the manifest code for the new app's credentials."""
        data = http.post_form(
            f"https://api.github.com/app-manifests/{quote(code, safe='')}/conversions",
            {},
            {
                "accept": "application/vnd.github+json",
                "x-github-api-version": API_VERSION,
            },
        )

        if not data.get("client_id") or not data.get("client_secret"):
            raise ProviderError("GitHub app creation failed")

        return data

    def installation_owner(
        self, access_token: str, installation_id: str
    ) -> Optional[str]:
        """The account an installation id belongs to."""
        try:
            data = http.get_json(
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

    def access(self, creds: Credentials, app_slug: Optional[str]) -> dict[str, Any]:
        api = (creds.base_url or "").rstrip("/") or "https://api.github.com"
        probe = Probe(
            {
                "authorization": f"Bearer {creds.token}",
                "x-github-api-version": API_VERSION,
            }
        )
        status, me = probe.get(f"{api}/user")

        if not me:
            return AccessReport.refused(self.label, status)

        report = AccessReport(
            kind=self.kind,
            login=me["login"],
            install_url=(
                f"https://github.com/apps/{app_slug}/installations/select_target"
                if app_slug
                else None
            ),
        )
        status, listing = probe.get(f"{api}/user/installations")

        if status in (403, 404):
            report.problems.append(
                "This token is not from a GitHub App (personal token): repositories are created with the token's own scopes. Needs `repo` and `workflow`."
            )

            return report.as_dict()

        for i in (listing or {}).get("installations", []):
            report.installations.append(self._installation(api, probe, i))

        self._check(report, me["login"])

        return report.as_dict()

    def _installation(self, api: str, probe: Probe, i: dict[str, Any]) -> Owner:
        org = i["account"].get("type") == "Organization"
        login = i["account"]["login"]
        selected = None

        if i.get("repository_selection") != "all":
            _, repos = probe.get(
                f"{api}/user/installations/{i['id']}/repositories?per_page=100"
            )
            selected = [r["full_name"] for r in (repos or {}).get("repositories", [])]

        return Owner(
            account=login,
            kind="org" if org else "user",
            repositories="all"
            if i.get("repository_selection") == "all"
            else "selected",
            administration=(i.get("permissions") or {}).get("administration", "none"),
            contents=(i.get("permissions") or {}).get("contents", "none"),
            selected=selected,
            configure_url=(
                f"https://github.com/organizations/{login}/settings/installations/{i['id']}"
                if org
                else f"https://github.com/settings/installations/{i['id']}"
            ),
        )

    @staticmethod
    def _check(report: AccessReport, login: str) -> None:
        if not report.installations:
            report.problems.append(
                f"The GitHub App is not installed on any account this token can see. Install it on {login} (or the organization that owns the repositories) with access to all repositories."
            )

        for i in report.installations:
            if i.administration != "write":
                report.problems.append(
                    f'{i.account}: repository permission "Administration" is {i.administration}; it must be "Read and write" to create repositories. Change it in the app\'s Permissions & events, then accept the new permissions on the installation.'
                )

            if i.contents != "write":
                report.problems.append(
                    f'{i.account}: repository permission "Contents" is {i.contents}; it must be "Read and write" to push.'
                )

            if i.repositories != "all":
                report.problems.append(
                    f"{i.account}: installed on selected repositories only; new repositories created by the platform will not be reachable. Switch the installation to all repositories."
                )
