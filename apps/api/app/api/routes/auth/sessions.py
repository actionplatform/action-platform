"""Sign up, sign in, sign out, the current session and the browser sessions of a user."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select

from app.api.dependencies import (
    AuthDep,
    DbDep,
)
from app.api.routes.auth.support import (
    current_session,
    identity_out,
    limited,
    signed,
)
from app.services.auth.service import (
    AuthService,
)
from app.core.db.models import (
    Organization,
    Session,
)
from app.schemas import auth as schemas

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
def status(
    request: Request,
    db: DbDep,
) -> schemas.AuthStatus:
    configured = request.app.state.secrets is not None
    users = AuthService(db, request.app.state.secrets).user_count() if configured else 0
    organizations = db.scalar(select(func.count()).select_from(Organization)) or 0

    return schemas.AuthStatus(
        configured=configured, users=users, organizations=organizations
    )


@router.post("/sign-up", status_code=201, dependencies=[Depends(limited("sign-up"))])
def sign_up(
    body: schemas.SignUpRequest,
    auth: AuthDep,
) -> schemas.Signed:
    user, session = auth.sign_up(
        body.name, body.email, body.password, body.invitation_id
    )

    return signed(auth, user, session)


@router.post("/sign-in", dependencies=[Depends(limited("sign-in"))])
def sign_in(
    body: schemas.SignInRequest,
    auth: AuthDep,
) -> schemas.Signed:
    user, session = auth.sign_in(
        body.email, body.password, body.ip_address, body.user_agent
    )

    return signed(auth, user, session)


@router.post("/sign-out", status_code=204)
def sign_out(
    auth: AuthDep,
    session: Session = Depends(current_session),
) -> Response:
    auth.sign_out(session.token)

    return Response(status_code=204)


@router.get("/session")
def session(
    auth: AuthDep,
    session: Session = Depends(current_session),
) -> schemas.IdentityOut:
    return identity_out(auth, auth.identity_of(session))


@router.post("/session/organization")
def set_active_organization(
    body: schemas.ActiveOrganizationRequest,
    auth: AuthDep,
    session: Session = Depends(current_session),
) -> schemas.IdentityOut:
    auth.set_active_organization(session, body.organization_id)

    return identity_out(auth, auth.identity_of(session))


@router.get("/sessions")
def sessions(
    auth: AuthDep,
    session: Session = Depends(current_session),
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
    auth: AuthDep,
    session: Session = Depends(current_session),
) -> Response:
    if not auth.revoke_session(session.user_id, id):
        raise HTTPException(404, "no such session")

    return Response(status_code=204)
