"""Teams and members."""

from typing import Optional

from action_platform.core.access import ROLE_LABELS
from fastapi import APIRouter, Depends, Header

from app.api.dependencies import (
    allowed,
    get_caller,
    get_directory,
    get_writes,
    manageable,
    org_of,
    required_org,
)
from app.schemas import directory as dschemas
from app.schemas import management as schemas
from app.services.access.caller import Caller
from app.services.directory import DirectoryService, DirectoryWrites


router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/teams")
def teams(
    x_organization: Optional[str] = Header(default=None),
    organization: Optional[str] = None,
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
) -> list[dschemas.TeamRow]:
    org = required_org(caller, x_organization, organization)

    return [
        dschemas.TeamRow(
            id=t.id,
            name=t.name,
            slug=t.slug,
            description=t.description,
            members=[
                dschemas.TeamMemberRow(userId=u.id, name=u.name, email=u.email)
                for u in directory.team_members_of(t.id)
            ],
            projects=[
                dschemas.Named(id=p.id, name=p.name)
                for p in directory.team_projects_of(t.id)
            ],
        )
        for t in directory.teams_of(org.id)
    ]


@router.get("/members")
def members(
    x_organization: Optional[str] = Header(default=None),
    organization: Optional[str] = None,
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
) -> list[dschemas.MemberRow]:
    org = required_org(caller, x_organization, organization)

    return [
        dschemas.MemberRow(
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
    body: dschemas.CreateTeamRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
) -> dschemas.Created:
    org = required_org(caller, x_organization, None)
    manageable(caller, org, "teams")
    team = directory.create_team(org.id, body.name, body.description or "")

    return dschemas.Created(id=team.id, name=team.name, slug=team.slug)


@router.post("/teams/members")
def add_team_member(
    body: dschemas.TeamMemberRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
) -> dschemas.Ok:
    org = required_org(caller, x_organization, None)
    manageable(caller, org, "teams/members")
    directory.add_team_member(org.id, body.team_id, body.user_id)

    return dschemas.Ok()


@router.post("/members/role")
def set_member_role(
    body: dschemas.MemberRoleRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
) -> dschemas.Ok:
    org = required_org(caller, x_organization, None)
    manageable(caller, org, "members/role")
    directory.set_member_role(org.id, body.user_id, body.role)

    return dschemas.Ok()


@router.put("/teams/{team_id}")
def update_team(
    team_id: str,
    body: schemas.TeamUpdate,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> dict:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    team = writes.update_team(org.id, team_id, body.name, body.description or "")

    return {"id": team.id, "name": team.name, "slug": team.slug}


@router.delete("/teams/{team_id}", status_code=204)
def delete_team(
    team_id: str,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> None:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    writes.delete_team(org.id, team_id)


@router.delete("/teams/{team_id}/members/{user_id}", status_code=204)
def remove_team_member(
    team_id: str,
    user_id: str,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> None:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    writes.remove_team_member(org.id, team_id, user_id)


@router.delete("/members/{user_id}", status_code=204)
def remove_member(
    user_id: str,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> None:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    writes.remove_member(org.id, user_id)
