"""GitHub access built into the platform, on the organization's own GitHub connection (Settings → Git): the OAuth host first, then one added with a token; the connection's owner is the GitHub organization it manages."""

from __future__ import annotations

from typing import Optional

from action_platform.core.service_access import AccessError
from action_platform.providers.access.github import (
    API_URL,
    BranchProtection,
    GitHubProvider,
    Org,
    OrgSettings,
    client,
)
from app.core.auth.crypto import Sealer
from app.core.db.database import Database
from app.services.integrations.hosts.credentials import FreshCredentials

KIND = "github"
NOT_CONNECTED = (
    "github: connect GitHub under Settings → Git with an owner of the organization"
)


class GitHubConnection:
    def __init__(
        self, database: Database, sealer: Optional[Sealer], organization_id: str
    ) -> None:
        self.database = database
        self.sealer = sealer
        self.organization_id = organization_id

    def provider(self) -> Optional[GitHubProvider]:
        """The `github` access provider, or None while the organization has no GitHub connection."""
        found = self._resolve()

        if found is None:
            return None

        org, token, url, app = found

        return GitHubProvider(org, token, url, http=client(token, url), app=app)

    def checks(self) -> Org:
        found = self._resolve()

        if found is None:
            raise AccessError(NOT_CONNECTED)

        org, token, url, _ = found

        return Org(client(token, url), org)

    def branch_protection(self, repo: Optional[str] = None) -> BranchProtection:
        return self.checks().branch_protection(repo)

    def repo_settings(self, repo: Optional[str] = None) -> OrgSettings:
        return self.checks().repo_settings(repo)

    def _resolve(self) -> Optional[tuple[str, str, str, Optional[str]]]:
        with self.database.session() as s:
            reads = FreshCredentials(s, self.sealer)
            hosts = sorted(
                (h for h in reads.hosts_of(self.organization_id) if h.kind == KIND),
                key=lambda h: h.auth_kind != "oauth",
            )

            if not hosts:
                return None

            host = hosts[0]
            owner, url = host.default_owner, host.base_url
            creds = reads.credentials_for(self.organization_id, host.id)
            app = reads.oauth_app(KIND) if host.auth_kind == "oauth" else None
            s.commit()

        if creds is None:
            raise AccessError(
                "github: the GitHub connection cannot be read; reconnect GitHub under Settings → Git"
            )

        if not owner:
            raise AccessError(
                "github: set the GitHub organization as the owner of the GitHub connection under Settings → Git"
            )

        return (owner, creds.token, url or API_URL, app.slug if app else None)
