from typing import Iterator, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from action_platform.api.auth.errors import Unauthenticated
from action_platform.api.auth.service import (
    DEVICE_TTL,
    SESSION_TTL,
    AuthService,
    Identity,
)
from action_platform.api.core.deps import get_db
from action_platform.api.core.ratelimit import RateLimiter
from action_platform.api.db.models import (
    ApiToken,
    App,
    DeviceCode,
    Organization,
    Project,
    Session,
)
from action_platform.api.schemas import auth as schemas
from action_platform.core.access import Grant, grants_of, parse_scopes

router = APIRouter(prefix="/api/auth", tags=["auth"])

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


def get_auth(
    request: Request, db: DbSession = Depends(get_db)
) -> Iterator[AuthService]:
    secrets = request.app.state.secrets
    if secrets is None:
        raise HTTPException(503, "auth is not configured: set AP_AUTH_SECRET")
    yield AuthService(db, secrets, request.app.state.verification_uri)


def current_session(
    auth: AuthService = Depends(get_auth),
    x_session_token: Optional[str] = Header(default=None),
    x_session_cookie: Optional[str] = Header(default=None),
) -> Session:
    session = (
        auth.session_from_token(x_session_token)
        if x_session_token
        else auth.session_from_cookie(x_session_cookie)
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


@router.get("/status")
def status(request: Request, db: DbSession = Depends(get_db)) -> schemas.AuthStatus:
    configured = request.app.state.secrets is not None
    users = AuthService(db, request.app.state.secrets).user_count() if configured else 0
    return schemas.AuthStatus(configured=configured, users=users)


@router.post("/sign-up", status_code=201, dependencies=[Depends(limited("sign-up"))])
def sign_up(
    body: schemas.SignUpRequest, auth: AuthService = Depends(get_auth)
) -> schemas.Signed:
    user, session = auth.sign_up(
        body.name, body.email, body.password, body.invitation_id
    )
    return signed(auth, user, session)


@router.post("/sign-in", dependencies=[Depends(limited("sign-in"))])
def sign_in(
    body: schemas.SignInRequest, auth: AuthService = Depends(get_auth)
) -> schemas.Signed:
    user, session = auth.sign_in(
        body.email, body.password, body.ip_address, body.user_agent
    )
    return signed(auth, user, session)


@router.post("/sign-out", status_code=204)
def sign_out(
    session: Session = Depends(current_session), auth: AuthService = Depends(get_auth)
) -> Response:
    auth.sign_out(session.token)
    return Response(status_code=204)


@router.get("/session")
def session(
    session: Session = Depends(current_session), auth: AuthService = Depends(get_auth)
) -> schemas.IdentityOut:
    return identity_out(auth, auth.identity_of(session))


@router.post("/session/organization")
def set_active_organization(
    body: schemas.ActiveOrganizationRequest,
    session: Session = Depends(current_session),
    auth: AuthService = Depends(get_auth),
) -> schemas.IdentityOut:
    auth.set_active_organization(session, body.organization_id)
    return identity_out(auth, auth.identity_of(session))


@router.get("/sessions")
def sessions(
    session: Session = Depends(current_session), auth: AuthService = Depends(get_auth)
) -> list[schemas.BrowserSessionOut]:
    rows = auth.sessions_of(session.user_id)
    return sorted(
        (
            schemas.BrowserSessionOut(
                id=s.id,
                created_at=s.created_at,
                updated_at=s.updated_at,
                expires_at=s.expires_at,
                ip_address=s.ip_address,
                user_agent=s.user_agent,
                current=s.id == session.id,
            )
            for s in rows
        ),
        key=lambda s: (not s.current, -s.updated_at.timestamp()),
    )


@router.delete("/sessions/{id}", status_code=204)
def revoke_session(
    id: str,
    session: Session = Depends(current_session),
    auth: AuthService = Depends(get_auth),
) -> Response:
    if not auth.revoke_session(session.user_id, id):
        raise HTTPException(404, "no such session")
    return Response(status_code=204)


@router.post("/organizations", status_code=201)
def create_organization(
    body: schemas.CreateOrganizationRequest,
    session: Session = Depends(current_session),
    auth: AuthService = Depends(get_auth),
) -> schemas.OrganizationOut:
    return organization_out(
        auth.create_organization(
            session, body.name, body.slug, body.git_author_name, body.git_author_email
        )
    )


@router.post("/members", status_code=201)
def add_member(
    body: schemas.AddMemberRequest,
    session: Session = Depends(current_session),
    auth: AuthService = Depends(get_auth),
) -> schemas.MemberAdded:
    user, existed = auth.add_member_account(
        session, body.organization_id, body.name, body.email, body.password, body.role
    )
    return schemas.MemberAdded(user_id=user.id, existed=existed)


@router.post("/device/code", dependencies=[Depends(limited("device-code"))])
def device_code(
    body: schemas.DeviceCodeRequest, auth: AuthService = Depends(get_auth)
) -> schemas.DeviceCodeOut:
    code = auth.device_code(body.client_id, body.scope)
    return schemas.DeviceCodeOut(
        device_code=code.device_code,
        user_code=code.user_code,
        verification_uri=auth.verification_uri,
        verification_uri_complete=f"{auth.verification_uri}?user_code={code.user_code}",
        expires_in=int(DEVICE_TTL.total_seconds()),
        interval=code.polling_interval or 0,
    )


@router.post("/device/token", dependencies=[Depends(limited("device-token"))])
def device_token(
    body: schemas.DeviceTokenRequest, auth: AuthService = Depends(get_auth)
) -> schemas.DeviceTokenOut:
    if body.grant_type != "urn:ietf:params:oauth:grant-type:device_code":
        raise HTTPException(400, "unsupported grant_type")
    session, scope = auth.device_token(body.device_code, body.client_id)
    return schemas.DeviceTokenOut(
        access_token=session.token,
        scope=scope,
        expires_in=int(SESSION_TTL.total_seconds()),
    )


@router.get("/device")
def device_request(
    user_code: str,
    session: Session = Depends(current_session),
    auth: AuthService = Depends(get_auth),
) -> schemas.DeviceRequestOut:
    code = auth.device_request(user_code)
    if code is None:
        raise HTTPException(404, "invalid code")
    return device_request_out(auth, code)


def device_request_out(auth: AuthService, code: DeviceCode) -> schemas.DeviceRequestOut:
    grant = Grant.parse(code.scope)
    return schemas.DeviceRequestOut(
        status=auth.device_status(code),
        requested=grant.scope,
        grant=grant_out(grant),
        client_id=code.client_id,
        expires_at=code.expires_at,
    )


@router.post("/device/approve")
def device_approve(
    body: schemas.DeviceDecision,
    session: Session = Depends(current_session),
    auth: AuthService = Depends(get_auth),
) -> schemas.DeviceDecisionOut:
    if body.grant is not None:
        auth.device_grant(session, body.user_code, grant_of(body.grant))
    return schemas.DeviceDecisionOut(
        status=auth.device_approve(session, body.user_code).status
    )


@router.post("/device/deny")
def device_deny(
    body: schemas.DeviceDecision,
    session: Session = Depends(current_session),
    auth: AuthService = Depends(get_auth),
) -> schemas.DeviceDecisionOut:
    return schemas.DeviceDecisionOut(
        status=auth.device_deny(session, body.user_code).status
    )


@router.post("/tokens", status_code=201)
def issue_token(
    body: schemas.IssueTokenRequest,
    session: Session = Depends(current_session),
    auth: AuthService = Depends(get_auth),
) -> schemas.TokenIssued:
    grant = Grant.parse(body.scope)
    grant = Grant(
        grant.scope,
        body.organization_id or grant.organization_id,
        body.project_id or grant.project_id,
        body.app_id or grant.app_id,
    )
    token, raw = auth.issue_token(session, grant, body.name)
    return schemas.TokenIssued(
        id=token.id,
        token=raw,
        scope=parse_scopes(token.scope),
        expires_at=token.expires_at,
    )


@router.get("/tokens")
def tokens(
    organization_id: Optional[str] = None,
    session: Session = Depends(current_session),
    auth: AuthService = Depends(get_auth),
) -> list[schemas.TokenOut]:
    rows = auth.tokens_of(session.user_id, organization_id)
    clients = auth.clients_of(rows)
    return [token_out(auth, t, clients.get(t.id, [])) for t in rows]


def token_out(auth: AuthService, token: ApiToken, clients) -> schemas.TokenOut:
    db = auth.db

    def named(model, id: Optional[str], fallback: str) -> Optional[schemas.Named]:
        if not id:
            return None
        name = db.scalar(select(model.name).where(model.id == id))
        return schemas.Named(id=id, name=name or fallback)

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


@router.delete("/tokens/{id}", status_code=204)
def revoke_token(
    id: str,
    session: Session = Depends(current_session),
    auth: AuthService = Depends(get_auth),
) -> Response:
    if not auth.revoke_token(session.user_id, id):
        raise HTTPException(404, "no such token")
    return Response(status_code=204)


@router.post("/tokens/verify")
def verify_token(
    body: schemas.VerifyTokenRequest, auth: AuthService = Depends(get_auth)
) -> schemas.TokenClaimsOut:
    token = auth.verify_token(body.token, body.client)
    if token is None:
        raise Unauthenticated("token is invalid, expired or revoked")
    user = token.user
    organizations = auth.organizations_of(user.id)
    organization = (
        next((o for o in organizations if o.id == token.organization_id), None)
        if token.organization_id
        else None
    )
    if token.organization_id and organization is None:
        raise Unauthenticated("you are no longer a member of the token's organization")
    return schemas.TokenClaimsOut(
        id=token.id,
        user=user_out(user),
        organization=organization_out(organization) if organization else None,
        organizations=[organization_out(o) for o in organizations],
        all_organizations=token.organization_id is None,
        scope=parse_scopes(token.scope),
        project_id=token.project_id,
        app_id=token.app_id,
        role=auth.role_in(user.id, organization.id) if organization else None,
    )
