"""Invitations into the organization."""

from fastapi import APIRouter

from app.api.dependencies import (
    CallerDep,
    OrgDep,
    WritesDep,
    allowed,
)
from app.schemas import organization as schemas

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/invitations")
def invitations(
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> list[schemas.InvitationRow]:
    allowed(caller, org, "org.manage")

    return [
        schemas.InvitationRow(
            id=i.id,
            email=i.email,
            role=i.role,
            status=i.status,
            expires_at=i.expires_at,
            created_at=i.created_at,
            inviter=u.name,
        )
        for i, u in writes.invitations_of(org.id)
    ]


@router.post("/invitations", status_code=201)
def invite(
    body: schemas.InviteRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> schemas.InvitationRow:
    allowed(caller, org, "org.manage")
    i = writes.create_invitation(org.id, caller.user.id, body.email, body.role)

    return schemas.InvitationRow(
        id=i.id,
        email=i.email,
        role=i.role,
        status=i.status,
        expires_at=i.expires_at,
        created_at=i.created_at,
        inviter=caller.user.name,
    )


@router.delete("/invitations/{id}", status_code=204)
def cancel_invitation(
    id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> None:
    allowed(caller, org, "org.manage")
    writes.cancel_invitation(org.id, id)
