"""Bitbucket: OAuth consumers, workspaces and their permissions."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

from action_platform.core.exception import ProviderError
from app.core.abc import HostProvider
from app.core.shared.credentials import Credentials, OAuthApp
from app.core.shared.http import BasicAuth, http
from app.services.integrations.hosts.access import AccessReport, Owner, Probe
from app.services.integrations.hosts.tokens import TokenResponse

API = "https://api.bitbucket.org/2.0"


class BitbucketProvider(HostProvider):
    kind = "bitbucket"
    label = "Bitbucket"
    scopes = ""
    token_username = "x-token-auth"
    callback_hint = "Bitbucket → Workspace settings → OAuth consumers (permissions: account, repositories write/admin/delete, pull requests write)"

    def web_base(self, app: OAuthApp) -> str:
        return "https://bitbucket.org"

    def api_base(self, app: OAuthApp) -> str:
        return API

    def stored_base_url(self, app: OAuthApp) -> Optional[str]:
        return None

    def authorize_url(self, app: OAuthApp, origin: str, state: str) -> str:
        params = {
            "client_id": app.client_id,
            "redirect_uri": self.callback_url(origin),
            "state": state,
            "response_type": "code",
        }

        return f"https://bitbucket.org/site/oauth2/authorize?{urlencode(params)}"

    def exchange_code(
        self, app: OAuthApp, origin: str, code: str
    ) -> tuple[str, Optional[str], Optional[datetime]]:
        data = http.post_form(
            "https://bitbucket.org/site/oauth2/access_token",
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.callback_url(origin),
            },
            {"authorization": BasicAuth.header(app.client_id, app.client_secret)},
        )

        return TokenResponse(data).read()

    def refresh(
        self, app: OAuthApp, refresh_token: str
    ) -> tuple[str, Optional[str], Optional[datetime]]:
        data = http.post_form(
            "https://bitbucket.org/site/oauth2/access_token",
            {"grant_type": "refresh_token", "refresh_token": refresh_token},
            {"authorization": BasicAuth.header(app.client_id, app.client_secret)},
        )

        return TokenResponse(data).read()

    def identity(self, app: OAuthApp, access_token: str) -> tuple[str, Optional[str]]:
        user = http.get_json(f"{API}/user", {"authorization": f"Bearer {access_token}"})

        if not user.get("username"):
            raise ProviderError("Bitbucket: could not read the signed-in user")

        return user["username"], user.get("display_name")

    def owner(self, access_token: str, installation_id: Optional[str]) -> Optional[str]:
        return self.first_workspace(access_token)

    def first_workspace(self, access_token: str) -> Optional[str]:
        """The workspace new repositories default to: owned first, then collaborated, then any."""
        try:
            data = http.get_json(
                f"{API}/user/permissions/workspaces?pagelen=100",
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

    def access(self, creds: Credentials, app_slug: Optional[str]) -> AccessReport:
        auth = (
            BasicAuth.header(creds.username, creds.token)
            if creds.username
            else f"Bearer {creds.token}"
        )
        probe = Probe({"authorization": auth})
        status, me = probe.get(f"{API}/user")

        if not me:
            return AccessReport.refused(self.kind, self.label, status)

        spaces_status, spaces = probe.get(
            f"{API}/user/permissions/workspaces?pagelen=100"
        )
        report = AccessReport(kind=self.kind, login=me["username"])
        report.installations = [
            Owner(
                w["workspace"]["slug"],
                "org",
                "all",
                "write" if w.get("permission") in ("owner", "collaborator") else "none",
                "write",
            )
            for w in (spaces or {}).get("values", [])
        ]

        if not report.installations:
            _, member = probe.get(f"{API}/workspaces?role=member&pagelen=100")
            report.installations = [
                Owner(w["slug"], "org", "all", "write", "write")
                for w in (member or {}).get("values", [])
            ]

        if not report.installations:
            report.problems.append(
                f"Bitbucket lists no workspace for this account (permissions endpoint answered {spaces_status}). The OAuth consumer needs Workspace membership: Read and Account: Read; repositories are created inside a workspace, never under the account name."
            )

        return report
