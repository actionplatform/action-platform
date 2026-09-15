"""Opening and accepting an invitation."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import (
    AuthDep,
    DbDep,
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
from app.services.directory import DirectoryWrites

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/invitations/{id}")
def open_invitation(
    id: str,
    db: DbDep,
) -> schemas.OpenInvitation:
    found = DirectoryWrites(db).invitation(id)

    if found is None:
        raise HTTPException(404, "invitation not found")

    invitation, inviter, organization = found

    return schemas.OpenInvitation(
        id=invitation.id,
        email=invitation.email,
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
    organization = DirectoryWrites(auth.db).accept_invitation(id, identity.user)
    session.active_organization_id = organization.id
    auth.db.flush()

    return organization_out(organization)
