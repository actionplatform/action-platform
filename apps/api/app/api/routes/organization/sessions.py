"""API tokens: issued, listed, revoked, verified."""

from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Response

from action_platform.core.access import Grant, parse_scopes
from app.api.dependencies import (
    AuthDep,
    ProjectsRepoDep,
    org_dict,
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
from app.schemas.common import AppRef, Named, Page, paged
from app.services.organization.sessions import TokenMinter

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/tokens", status_code=201)
def issue_token(
    body: schemas.IssueTokenRequest,
    auth: AuthDep,
    directory: ProjectsRepoDep,
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
    minted = TokenMinter(auth, directory).minted(
        token, raw, auth.organizations_of(session.user_id)
    )
    organization, project, app = minted.organization, minted.project, minted.app

    return schemas.TokenIssued(
        id=token.id,
        token=raw,
        scope=parse_scopes(token.scope),
        expires_at=token.expires_at,
        organization=org_dict(organization) if organization else None,
        organizations=None
        if organization
        else [org_dict(o) for o in auth.organizations_of(session.user_id)],
        project=Named(id=project.id, name=project.name) if project else None,
        app=AppRef(id=app.id, name=app.name, registry_id=app.registry_id)
        if app
        else None,
    )


@router.get("/tokens")
def tokens(
    auth: AuthDep,
    organization_id: Optional[str] = None,
    page: Optional[int] = None,
    per: int = 10,
    session: Session = Depends(current_session),
) -> Union[list[schemas.TokenOut], Page[schemas.TokenOut]]:
    rows = auth.tokens_of(session.user_id, organization_id)
    clients = auth.clients_of(rows)

    return paged([token_out(auth, t, clients.get(t.id, [])) for t in rows], page, per)


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
