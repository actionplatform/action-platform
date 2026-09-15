"""GitLab: OAuth and the groups the account can create projects in."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlencode

from action_platform_api.core.abc import HostProvider
from action_platform_api.services.hosts.access import AccessReport, Owner, Probe
from action_platform_api.services.hosts.tokens import TokenResponse
from action_platform_api.core.shared.credentials import Credentials, OAuthApp
from action_platform_api.core.shared.http import http
from action_platform.core.exception import ProviderError


class GitlabProvider(HostProvider):
    kind = "gitlab"
    label = "GitLab"
    scopes = "api write_repository read_user"
    callback_hint = (
        "GitLab → User settings → Applications (or group/instance applications)"
    )

    def web_base(self, app: OAuthApp) -> str:
        return (app.base_url or "https://gitlab.com").rstrip("/")

    def api_base(self, app: OAuthApp) -> str:
        return f"{self.web_base(app)}/api/v4"

    def stored_base_url(self, app: OAuthApp) -> Optional[str]:
        return self.web_base(app) if app.base_url else None

    def authorize_url(self, app: OAuthApp, origin: str, state: str) -> str:
        params = {
            "client_id": app.client_id,
            "redirect_uri": self.callback_url(origin),
            "state": state,
            "response_type": "code",
            "scope": self.scopes,
        }

        return f"{self.web_base(app)}/oauth/authorize?{urlencode(params)}"

    def exchange_code(
        self, app: OAuthApp, origin: str, code: str
    ) -> tuple[str, Optional[str], Optional[datetime]]:
        data = http.post_form(
            f"{self.web_base(app)}/oauth/token",
            {
                "client_id": app.client_id,
                "client_secret": app.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.callback_url(origin),
            },
        )

        return TokenResponse(data).read()

    def refresh(
        self, app: OAuthApp, refresh_token: str
    ) -> tuple[str, Optional[str], Optional[datetime]]:
        data = http.post_form(
            f"{self.web_base(app)}/oauth/token",
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

        if not user.get("username"):
            raise ProviderError("GitLab: could not read the signed-in user")

        return user["username"], user.get("name")

    def access(self, creds: Credentials, app_slug: Optional[str]) -> dict[str, Any]:
        api = (
            re.sub(
                r"/api/v4$",
                "",
                (creds.base_url or "").rstrip("/") or "https://gitlab.com",
            )
            + "/api/v4"
        )
        probe = Probe({"authorization": f"Bearer {creds.token}"})
        status, me = probe.get(f"{api}/user")

        if not me:
            return AccessReport.refused(self.label, status)

        groups_status, groups = probe.get(
            f"{api}/groups?min_access_level=30&per_page=100&order_by=path"
        )
        can_create = me.get("can_create_project") is not False
        report = AccessReport(kind=self.kind, login=me["username"])
        report.installations.append(
            Owner(
                me["username"],
                "user",
                "all",
                "write" if can_create else "none",
                "write",
            )
        )
        report.installations += [
            Owner(g["full_path"], "org", "all", "write", "write")
            for g in (groups or [])
        ]

        if not can_create:
            report.problems.append(
                f"{me['username']} cannot create projects in the personal namespace; pick a group instead."
            )

        if groups_status != 200:
            report.problems.append(
                "Could not list groups: the token needs the `api` scope."
            )

        return report.as_dict()
