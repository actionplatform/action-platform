"""Teams and members."""

from typing import Optional

from fastapi import APIRouter, Header

from action_platform.core.access import ROLE_LABELS
from app.api.dependencies import (
    CallerDep,
    OrgDep,
    OrganizationRepoDep,
    allowed,
    manageable,
    required_org,
)
from app.core.errors import Forbidden
from app.schemas import common
from app.schemas import organization as schemas

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/teams")
def teams(
    caller: CallerDep,
    directory: OrganizationRepoDep,
    x_organization: Optional[str] = Header(default=None),
    organization: Optional[str] = None,
) -> list[schemas.TeamRow]:
    org = required_org(caller, x_organization, organization)

    return [
        schemas.TeamRow(
            id=t.id,
            name=t.name,
            slug=t.slug,
            description=t.description,
            members=[
                schemas.TeamMemberRow(userId=u.id, name=u.name, email=u.email)
                for u in directory.team_members_of(t.id)
            ],
            projects=[
                common.Named(id=p.id, name=p.name)
                for p in directory.team_projects_of(t.id)
            ],
        )
        for t in directory.teams_of(org.id)
    ]


@router.get("/members")
def members(
    caller: CallerDep,
    directory: OrganizationRepoDep,
    x_organization: Optional[str] = Header(default=None),
    organization: Optional[str] = None,
) -> list[schemas.MemberRow]:
    org = required_org(caller, x_organization, organization)

    return [
        schemas.MemberRow(
            user_id=u.id,
            name=u.name,
            email=u.email,
            role=m.role,
            role_label=ROLE_LABELS.get(m.role, m.role),
        )
        for m, u in directory.members_of(org.id)
    ]


@router.post("/teams", status_code=201)
def create_team(
    body: schemas.CreateTeamRequest,
    caller: CallerDep,
    directory: OrganizationRepoDep,
    x_organization: Optional[str] = Header(default=None),
) -> common.Created:
    org = required_org(caller, x_organization, None)
    manageable(caller, org, "teams")
    team = directory.create_team(org.id, body.name, body.description or "")

    return common.Created(id=team.id, name=team.name, slug=team.slug)


@router.post("/teams/members")
def add_team_member(
    body: schemas.TeamMemberRequest,
    caller: CallerDep,
    directory: OrganizationRepoDep,
    x_organization: Optional[str] = Header(default=None),
) -> common.Ok:
    org = required_org(caller, x_organization, None)
    manageable(caller, org, "teams/members")
    directory.add_team_member(org.id, body.team_id, body.user_id)

    return common.Ok()


@router.post("/members/role")
def set_member_role(
    body: schemas.MemberRoleRequest,
    caller: CallerDep,
    directory: OrganizationRepoDep,
    x_organization: Optional[str] = Header(default=None),
) -> common.Ok:
    org = required_org(caller, x_organization, None)
    manageable(caller, org, "members/role")
    current = directory.role_in(body.user_id, org.id)

    if (body.role == "owner" or current == "owner") and directory.role_in(
        caller.user.id, org.id
    ) != "owner":
        raise Forbidden("only an owner may give or take the owner role")

    directory.set_member_role(org.id, body.user_id, body.role)

    return common.Ok()


@router.put("/teams/{team_id}")
def update_team(
    team_id: str,
    body: schemas.TeamUpdate,
    org: OrgDep,
    caller: CallerDep,
    writes: OrganizationRepoDep,
) -> dict:
    allowed(caller, org, "org.manage")
    team = writes.update_team(org.id, team_id, body.name, body.description or "")

    return {"id": team.id, "name": team.name, "slug": team.slug}


@router.delete("/teams/{team_id}", status_code=204)
def delete_team(
    team_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: OrganizationRepoDep,
) -> None:
    allowed(caller, org, "org.manage")
    writes.delete_team(org.id, team_id)


@router.delete("/teams/{team_id}/members/{user_id}", status_code=204)
def remove_team_member(
    team_id: str,
    user_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: OrganizationRepoDep,
) -> None:
    allowed(caller, org, "org.manage")
    writes.remove_team_member(org.id, team_id, user_id)


@router.delete("/members/{user_id}", status_code=204)
def remove_member(
    user_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: OrganizationRepoDep,
) -> None:
    allowed(caller, org, "org.manage")

    if (
        writes.role_in(user_id, org.id) == "owner"
        and writes.role_in(caller.user.id, org.id) != "owner"
    ):
        raise Forbidden("only an owner may remove an owner")

    writes.remove_member(org.id, user_id)
