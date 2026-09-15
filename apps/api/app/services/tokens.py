"""Minting a scoped API token for the CLI or MCP from a browser session, with what it reaches resolved for the answer."""

from dataclasses import dataclass
from typing import Optional


from action_platform.core.access import Grant, parse_scopes
from app.core.auth.service import AuthService
from app.core.db.models import ApiToken, App, Organization, Project
from app.services.access.caller import Caller
from app.services.directory import DirectoryService
from app.core.errors import Forbidden, Invalid


@dataclass(frozen=True)
class MintedToken:
    token: ApiToken
    raw: str
    organization: Optional[Organization]
    project: Optional[Project]
    app: Optional[App]

    @property
    def scope(self) -> str:
        return Grant(
            parse_scopes(self.token.scope),
            self.token.organization_id or "*",
            self.token.project_id,
            self.token.app_id,
        ).format()


class TokenMinter:
    def __init__(self, auth: AuthService, directory: DirectoryService) -> None:
        self.auth = auth
        self.directory = directory

    def mint(self, caller: Caller, scope: str, name: Optional[str]) -> MintedToken:
        if caller.scope is not None or not caller.session_token:
            raise Forbidden("a token cannot mint another token; sign in again")

        grant = Grant.parse(scope)

        if not grant.scope:
            raise Invalid(
                "scope must include at least one of read, write, release, admin"
            )

        session = self.auth.require_session(caller.session_token)
        token, raw = self.auth.issue_token(
            session, grant, (name or "").strip()[:80] or "cli"
        )
        organization = (
            caller.member_of(token.organization_id) if token.organization_id else None
        )
        project = (
            self.directory.project(organization.id, token.project_id)
            if organization and token.project_id
            else None
        )
        app = (
            self.directory.app(project.id, token.app_id)
            if project and token.app_id
            else None
        )

        return MintedToken(token, raw, organization, project, app)
