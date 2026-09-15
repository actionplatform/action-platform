from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session as DbSession

from action_platform.core.access import PERMISSIONS, can, parse_scopes, scope_allows
from app.core.auth.cookies import SessionCookie
from app.core.auth.jwt import looks_like_jwt
from app.services.auth.service import AuthService
from app.core.db.models import Organization, User
from app.repositories.organization import OrganizationRepository


@dataclass
class Caller:
    """Who is calling `/api/v1`: the person, the organizations they belong to (with role), and what the token — if any — limits them to."""

    user: User
    organizations: list[tuple[Organization, Optional[str]]]
    organization: Optional[Organization]
    all_organizations: bool
    scope: Optional[list[str]]
    token_id: Optional[str]
    project_id: Optional[str]
    app_id: Optional[str]
    session_token: Optional[str]
    client: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def role_in(self, organization_id: Optional[str]) -> Optional[str]:
        return next(
            (role for org, role in self.organizations if org.id == organization_id),
            None,
        )

    def member_of(self, id_or_slug: str) -> Optional[Organization]:
        return next(
            (
                org
                for org, _ in self.organizations
                if org.id == id_or_slug or org.slug == id_or_slug
            ),
            None,
        )

    def allows(
        self, organization_id: Optional[str], permission: Optional[str]
    ) -> tuple[bool, str]:
        role = self.role_in(organization_id) if organization_id else None

        if organization_id and permission and not can(role, permission):
            return False, f"your role ({role or 'none'}) lacks {permission}"

        if self.scope is not None and not scope_allows(self.scope, permission):
            return (
                False,
                f"the token's scope ({' '.join(self.scope)}) does not allow {permission or 'read'}",
            )

        return True, ""

    def permissions_in(self, organization_id: Optional[str]) -> dict[str, bool]:
        role = self.role_in(organization_id) if organization_id else None

        return {
            p: (can(role, p) if organization_id else True)
            and (self.scope is None or scope_allows(self.scope, p))
            for p in PERMISSIONS
        }

    def within_reach(self, app_id: str, project_id: str) -> bool:
        if self.app_id:
            return app_id == self.app_id

        if self.project_id:
            return project_id == self.project_id

        return True


def resolve_caller(
    headers: dict[str, str], db: DbSession, auth: AuthService
) -> Optional[Caller]:
    directory = OrganizationRepository(db)
    authorization = headers.get("authorization", "")
    bearer = (
        authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    )
    client = (headers.get("x-action-platform-client") or "").strip()[:120] or None

    if bearer and looks_like_jwt(bearer):
        token = auth.verify_token(bearer, client)

        if token is None:
            return None

        organizations = directory.organizations_of(token.user_id)
        organization = (
            next((o for o, _ in organizations if o.id == token.organization_id), None)
            if token.organization_id
            else None
        )

        if token.organization_id and organization is None:
            return None

        return Caller(
            user=token.user,
            organizations=organizations,
            organization=organization,
            all_organizations=token.organization_id is None,
            scope=parse_scopes(token.scope),
            token_id=token.id,
            project_id=token.project_id,
            app_id=token.app_id,
            session_token=None,
            client=client,
        )

    session = None

    if bearer:
        session = auth.session_from_token(bearer)

    if session is None and headers.get("x-session-token"):
        session = auth.session_from_token(headers["x-session-token"])

    if session is None and headers.get("x-session-cookie"):
        session = auth.session_from_cookie(headers["x-session-cookie"])

    if session is None and headers.get("cookie"):
        session = auth.session_from_cookie(SessionCookie.value(headers["cookie"]))

    if session is None:
        return None

    identity = auth.identity_of(session)
    organizations = directory.organizations_of(identity.user.id)

    return Caller(
        user=identity.user,
        organizations=organizations,
        organization=identity.organization,
        all_organizations=False,
        scope=None,
        token_id=None,
        project_id=None,
        app_id=None,
        session_token=session.token,
        client=client,
    )
