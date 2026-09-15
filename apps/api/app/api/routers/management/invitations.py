"""Invitations into the organization."""

from typing import Optional

from fastapi import APIRouter, Depends, Header

from app.services.access.caller import Caller
from app.schemas import management as schemas
from app.services.directory import (
    DirectoryWrites,
)

from app.api.dependencies import (
    allowed,
    get_caller,
    get_writes,
    org_of,
)

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/invitations")
def invitations(
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> list[schemas.InvitationRow]:
    org = org_of(caller, x_organization)
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
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.InvitationRow:
    org = org_of(caller, x_organization)
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
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> None:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    writes.cancel_invitation(org.id, id)
