"""Opening and accepting an invitation."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import (
    AuthDep,
    DbDep,
    HostProvidersDep,
)
from app.api.routes.auth.support import (
    current_session,
    organization_out,
)
from app.services.auth.service import (
    now,
)
from app.core.db.models import (
    Session,
)
from app.schemas import auth as schemas
from app.repositories.organization import OrganizationRepository
from app.services.organization.invitations import InvitationProof

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/invitations/{id}")
def open_invitation(
    id: str,
    db: DbDep,
) -> schemas.OpenInvitation:
    found = OrganizationRepository(db).invitation(id)

    if found is None:
        raise HTTPException(404, "invitation not found")

    invitation, inviter, organization = found

    return schemas.OpenInvitation(
        id=invitation.id,
        email=invitation.email,
        login=invitation.host_login,
        host_kind=invitation.host_kind,
        role=invitation.role or "developer",
        status=invitation.status,
        expired=invitation.expires_at < now(),
        inviter=inviter.name,
        organization=organization_out(organization),
    )


@router.post("/invitations/{id}/accept")
def accept_invitation(
    id: str,
    auth: AuthDep,
    session: Session = Depends(current_session),
) -> schemas.OrganizationOut:
    identity = auth.identity_of(session)
    organization = OrganizationRepository(auth.db).accept_invitation(id, identity.user)
    session.active_organization_id = organization.id
    auth.db.flush()

    return organization_out(organization)


def proof(request: Request, auth: AuthDep, providers: HostProvidersDep):
    return InvitationProof(
        auth.db, request.app.state.sealer, request.app.state.secrets, providers
    )


@router.post("/invitations/{id}/verify")
def verify_login(
    id: str,
    body: schemas.VerifyLoginStart,
    auth: AuthDep,
    session: Session = Depends(current_session),
    proofs: InvitationProof = Depends(proof),
) -> schemas.VerifyLoginStarted:
    identity = auth.identity_of(session)

    return schemas.VerifyLoginStarted(
        url=proofs.start(id, identity.user, body.origin.rstrip("/"))
    )


@router.post("/invitations/{id}/verify/callback")
def verify_login_callback(
    id: str,
    body: schemas.VerifyLoginCallback,
    auth: AuthDep,
    session: Session = Depends(current_session),
    proofs: InvitationProof = Depends(proof),
) -> schemas.OrganizationOut:
    identity = auth.identity_of(session)
    organization = proofs.finish(
        id, identity.user, body.origin.rstrip("/"), body.code, body.state
    )
    session.active_organization_id = organization.id
    auth.db.flush()

    return organization_out(organization)
