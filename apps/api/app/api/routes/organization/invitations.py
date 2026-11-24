"""Invitations into the organization."""

from app.core.shared import people
from fastapi import APIRouter

from app.api.dependencies import (
    CallerDep,
    OrgDep,
    OrganizationRepoDep,
    allowed,
)
from app.core.db.models import Invitation, User
from app.core.errors import Forbidden, NotFound
from app.repositories.organization import OrganizationRepository
from app.repositories.organization.invitations import invitation_team_ids
from app.schemas import organization as schemas

router = APIRouter(prefix="/api/v1", tags=["management"])


def row(
    writes: OrganizationRepository, i: Invitation, inviter: User
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
    )


@router.get("/invitations")
def invitations(
    org: OrgDep,
    caller: CallerDep,
    writes: OrganizationRepoDep,
) -> list[schemas.InvitationRow]:
    allowed(caller, org, "org.manage")

    return [row(writes, i, u) for i, u in writes.invitations_of(org.id)]


@router.post("/invitations", status_code=201)
def invite(
    body: schemas.InviteRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: OrganizationRepoDep,
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

    return row(writes, i, caller.user)


@router.delete("/invitations/{id}", status_code=204)
def cancel_invitation(
    id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: OrganizationRepoDep,
) -> None:
    allowed(caller, org, "org.manage")
    writes.cancel_invitation(org.id, id)
