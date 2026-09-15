"""API tokens: issued, listed, revoked, verified."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response

from action_platform.core.access import Grant, parse_scopes
from app.api.dependencies import (
    AuthDep,
)
from app.api.routes.auth.support import (
    current_session,
    organization_out,
    token_out,
    user_out,
)
from app.services.auth.errors import Unauthenticated
from app.core.db.models import (
    Session,
)
from app.schemas import auth as schemas

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/tokens", status_code=201)
def issue_token(
    body: schemas.IssueTokenRequest,
    auth: AuthDep,
    session: Session = Depends(current_session),
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
    auth: AuthDep,
    organization_id: Optional[str] = None,
    session: Session = Depends(current_session),
) -> list[schemas.TokenOut]:
    rows = auth.tokens_of(session.user_id, organization_id)
    clients = auth.clients_of(rows)

    return [token_out(auth, t, clients.get(t.id, [])) for t in rows]


@router.delete("/tokens/{id}", status_code=204)
def revoke_token(
    id: str,
    auth: AuthDep,
    session: Session = Depends(current_session),
) -> Response:
    if not auth.revoke_token(session.user_id, id):
        raise HTTPException(404, "no such token")

    return Response(status_code=204)


@router.post("/tokens/verify")
def verify_token(
    body: schemas.VerifyTokenRequest,
    auth: AuthDep,
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
