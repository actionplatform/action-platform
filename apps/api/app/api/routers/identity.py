"""The platform as an OIDC issuer: discovery and keys for the clouds, a token for a caller who may release."""

from fastapi import APIRouter, HTTPException, Request

from app import schemas
from app.api.dependencies import CallerDep, DirectoryDep, OrgDep, allowed
from app.services.identity import TTL, IdentityIssuer, subject_for

router = APIRouter(tags=["identity"])


def issuer_of(request: Request) -> IdentityIssuer:
    state = request.app.state

    if state.db is None:
        raise HTTPException(503, "no database configured: set AP_DATABASE_URL")

    return IdentityIssuer(state.db, state.sealer, state.public_url)


@router.get("/.well-known/openid-configuration")
def openid_configuration(request: Request) -> dict:
    return issuer_of(request).configuration()


@router.get("/.well-known/jwks.json")
def jwks(request: Request) -> dict:
    return issuer_of(request).jwks()


@router.post("/api/v1/identity/token")
def identity_token(
    body: schemas.IdentityTokenRequest,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    directory: DirectoryDep,
) -> schemas.IdentityToken:
    """A short-lived token about the caller's organization (and project, app) for `audience` — what a local `action-platform deploy` hands to `sts assume-role-with-web-identity`."""
    allowed(caller, org, "app.release", whole_org=False)
    project = directory.project(org.id, body.project_id) if body.project_id else None
    app = directory.app(project.id, body.app_id) if project and body.app_id else None
    subject = subject_for(
        org.slug, project.slug if project else None, app.name if app else None
    )
    issuer = issuer_of(request)
    scopes = sorted(p for p, ok in caller.permissions_in(org.id).items() if ok)
    token = issuer.mint(
        subject,
        body.audience,
        organization=org.slug,
        project=project.slug if project else None,
        app=app.name if app else None,
        actor=caller.user.email,
        scopes=scopes,
    )

    return schemas.IdentityToken(
        token=token,
        subject=subject,
        audience=body.audience,
        expires_in=TTL,
        issuer=issuer.issuer,
    )
