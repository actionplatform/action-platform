"""Invitations into the organization."""

from typing import Optional, Union

from app.core.shared import people
from fastapi import APIRouter

from app.api.dependencies import (
    CallerDep,
    InvitationSenderDep,
    OrgDep,
    OrganizationRepoDep,
    allowed,
)
from app.core.db.models import Invitation, User
from app.core.errors import Conflict, Forbidden, NotFound
from app.repositories.organization import OrganizationRepository
from app.repositories.organization.invitations import invitation_team_ids
from app.schemas import organization as schemas
from app.schemas.common import Page, paged
from app.services.organization import email_state

router = APIRouter(prefix="/api/v1", tags=["management"])


def row(
    writes: OrganizationRepository, i: Invitation, inviter: User, enabled: bool
) -> schemas.InvitationRow:
    names = {t.id: t.name for t in writes.teams_of(i.organization_id)}

    return schemas.InvitationRow(
        id=i.id,
        email=i.email,
        login=i.host_login,
        host_kind=i.host_kind,
        teams=[names[t] for t in invitation_team_ids(i) if t in names],
        role=i.role,
        status=i.status,
        expires_at=i.expires_at,
        created_at=i.created_at,
        inviter=people.label(inviter) or "",
        emailed_at=i.emailed_at,
        email_error=i.email_error,
        email_state=email_state(i, enabled),
    )


@router.get("/invitations")
def invitations(
    org: OrgDep,
    caller: CallerDep,
    writes: OrganizationRepoDep,
    sender: InvitationSenderDep,
    page: Optional[int] = None,
    per: int = 10,
) -> Union[list[schemas.InvitationRow], Page[schemas.InvitationRow]]:
    allowed(caller, org, "org.manage")

    return paged(
        [row(writes, i, u, sender.enabled) for i, u in writes.invitations_of(org.id)],
        page,
        per,
    )


@router.post("/invitations", status_code=201)
def invite(
    body: schemas.InviteRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: OrganizationRepoDep,
    sender: InvitationSenderDep,
) -> schemas.InvitationRow:
    allowed(caller, org, "org.manage")

    if body.role == "owner" and writes.role_in(caller.user.id, org.id) != "owner":
        raise Forbidden("only an owner may give or take the owner role")

    for team_id in body.team_ids:
        if writes.team(org.id, team_id) is None:
            raise NotFound(f"team {team_id} not found")

    i = writes.create_invitation(
        org.id, caller.user.id, body.email, body.role, body.team_ids
    )

    if i.emailed_at is None:
        sender.send(writes, i.id)

    return row(writes, i, caller.user, sender.enabled)


@router.post("/invitations/{id}/resend")
def resend_invitation(
    id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: OrganizationRepoDep,
    sender: InvitationSenderDep,
) -> schemas.InvitationRow:
    """Send the invitation email again: same id, expiry renewed. A failed send is recorded on the invitation, not raised."""
    allowed(caller, org, "org.manage")

    if not sender.enabled:
        raise Conflict("email is not configured: set AP_SMTP_HOST")

    found = next(((i, u) for i, u in writes.invitations_of(org.id) if i.id == id), None)

    if found is None:
        raise NotFound("invitation not found")

    if not found[0].email:
        raise Conflict("this invitation is for a login, not an email: nothing to send")

    if found[0].role == "owner" and writes.role_in(caller.user.id, org.id) != "owner":
        raise Forbidden("only an owner may give or take the owner role")

    i = writes.renew_invitation(org.id, id)
    sender.send(writes, id)

    return row(writes, i, found[1], sender.enabled)


@router.delete("/invitations/{id}", status_code=204)
def cancel_invitation(
    id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: OrganizationRepoDep,
) -> None:
    allowed(caller, org, "org.manage")
    writes.cancel_invitation(org.id, id)
