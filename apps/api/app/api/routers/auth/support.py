"""What every auth route shares: rate limits, the current session, and how rows are shaped for the web app."""

from typing import Optional

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select

from app.core.auth.cookies import SessionCookie
from app.core.auth.errors import Unauthenticated
from app.core.auth.jwt import looks_like_jwt
from app.core.auth.service import (
    AuthService,
    Identity,
)
from app.api.dependencies import get_auth
from app.api.ratelimit import RateLimiter
from app.core.db.models import (
    ApiToken,
    App,
    DeviceCode,
    Organization,
    Project,
    Session,
)
from app.schemas import auth as schemas
from action_platform.core.access import Grant, grants_of, parse_scopes
from app.schemas import common


LIMITS = {
    "sign-in": RateLimiter(10, 60),
    "sign-up": RateLimiter(10, 60),
    "device-code": RateLimiter(20, 60),
    "device-token": RateLimiter(40, 60),
}


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")

    if forwarded:
        return forwarded.split(",")[0].strip()

    return request.client.host if request.client else "unknown"


def limited(name: str):
    def check(request: Request) -> None:
        if not LIMITS[name].allow(client_ip(request)):
            raise HTTPException(429, "too many attempts, wait a minute")

    return check


def current_session(
    request: Request,
    auth: AuthService = Depends(get_auth),
    x_session_token: Optional[str] = Header(default=None),
    x_session_cookie: Optional[str] = Header(default=None),
) -> Session:
    authorization = request.headers.get("authorization", "")
    bearer = (
        authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    )
    session = None

    if bearer and not looks_like_jwt(bearer):
        session = auth.session_from_token(bearer)

    if session is None and x_session_token:
        session = auth.session_from_token(x_session_token)

    if session is None and x_session_cookie:
        session = auth.session_from_cookie(x_session_cookie)

    if session is None and request.headers.get("cookie"):
        session = auth.session_from_cookie(
            SessionCookie.value(request.headers["cookie"])
        )

    if session is None:
        raise Unauthenticated()

    return session


def user_out(user) -> schemas.UserOut:
    return schemas.UserOut(
        id=user.id, name=user.name, email=user.email, image=user.image
    )


def session_out(auth: AuthService, session: Session) -> schemas.SessionOut:
    return schemas.SessionOut(
        id=session.id,
        token=session.token,
        cookie=auth.cookie_for(session),
        expires_at=session.expires_at,
        created_at=session.created_at,
        updated_at=session.updated_at,
        ip_address=session.ip_address,
        user_agent=session.user_agent,
        active_organization_id=session.active_organization_id,
    )


def organization_out(organization: Organization) -> schemas.OrganizationOut:
    return schemas.OrganizationOut(
        id=organization.id, name=organization.name, slug=organization.slug
    )


def identity_out(auth: AuthService, identity: Identity) -> schemas.IdentityOut:
    return schemas.IdentityOut(
        user=user_out(identity.user),
        session=session_out(auth, identity.session),
        organization=organization_out(identity.organization)
        if identity.organization
        else None,
        organizations=[
            organization_out(o) for o in auth.organizations_of(identity.user.id)
        ],
        role=identity.role,
        grants=grants_of(identity.role),
    )


def signed(auth: AuthService, user, session: Session) -> schemas.Signed:
    return schemas.Signed(user=user_out(user), session=session_out(auth, session))


def grant_of(body: Optional[schemas.GrantIn]) -> Grant:
    if body is None:
        return Grant()

    return Grant(
        parse_scopes(" ".join(body.scope)),
        body.organization_id or None,
        body.project_id or None,
        body.app_id or None,
    )


def grant_out(grant: Grant) -> schemas.GrantOut:
    return schemas.GrantOut(
        scope=grant.scope,
        organization_id=grant.organization_id,
        project_id=grant.project_id,
        app_id=grant.app_id,
    )


def device_request_out(auth: AuthService, code: DeviceCode) -> schemas.DeviceRequestOut:
    grant = Grant.parse(code.scope)

    return schemas.DeviceRequestOut(
        status=auth.device_status(code),
        requested=grant.scope,
        grant=grant_out(grant),
        client_id=code.client_id,
        expires_at=code.expires_at,
    )


def token_out(auth: AuthService, token: ApiToken, clients) -> schemas.TokenOut:
    db = auth.db

    def named(model, id: Optional[str], fallback: str) -> Optional[common.Named]:
        if not id:
            return None

        name = db.scalar(select(model.name).where(model.id == id))

        return common.Named(id=id, name=name or fallback)

    return schemas.TokenOut(
        id=token.id,
        name=token.name,
        scope=parse_scopes(token.scope),
        organization=named(Organization, token.organization_id, "deleted organization"),
        project=named(Project, token.project_id, "deleted project"),
        app=named(App, token.app_id, "deleted app"),
        created_at=token.created_at,
        expires_at=token.expires_at,
        last_used_at=token.last_used_at,
        clients=[
            schemas.TokenClientOut(
                name=c.name, first_seen_at=c.first_seen_at, last_seen_at=c.last_seen_at
            )
            for c in clients
        ],
    )
