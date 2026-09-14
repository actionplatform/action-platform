from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from action_platform.api.access.caller import Caller
from action_platform.api.auth.router import get_auth
from action_platform.api.auth.service import AuthService
from action_platform.api.core.deps import get_db
from action_platform.api.db.models import Organization
from action_platform.api.schemas import directory as schemas
from action_platform.api.services.directory import DirectoryService
from action_platform.api.services.jobs import JobQueue, job_view
from action_platform.core.access import (
    catalog,
    ROLE_LABELS,
    Grant,
    grantable_scopes,
    grants_of,
    parse_scopes,
)

router = APIRouter(prefix="/api/v1", tags=["v1"])

MANAGE = {
    "projects": "project.manage",
    "projects/team": "project.manage",
    "teams": "org.manage",
    "teams/members": "org.manage",
    "members/role": "org.manage",
}


def get_caller(request: Request) -> Caller:
    caller = getattr(request.state, "caller", None)

    if caller is None:
        raise HTTPException(401, "unauthorized")

    return caller


def get_directory(db: DbSession = Depends(get_db)) -> DirectoryService:
    return DirectoryService(db)


def org_dict(organization: Organization) -> dict:
    return {"id": organization.id, "name": organization.name, "slug": organization.slug}


def requested_org(
    caller: Caller, x_organization: Optional[str], organization: Optional[str]
) -> Optional[Organization]:
    wanted = (x_organization or organization or "").strip()

    if wanted and (caller.all_organizations or caller.scope is None):
        found = caller.member_of(wanted)

        if found is not None:
            return found

    return caller.organization


def required_org(
    caller: Caller, x_organization: Optional[str], organization: Optional[str]
) -> Organization:
    org = requested_org(caller, x_organization, organization)

    if org is None:
        raise HTTPException(
            400,
            "this token spans every organization: send X-Organization: <id or slug>",
        )

    return org


def manageable(caller: Caller, org: Organization, path: str) -> None:
    permission = MANAGE[path]
    ok, why = caller.allows(org.id, permission)

    if not ok:
        raise HTTPException(403, why)

    if caller.project_id or caller.app_id:
        raise HTTPException(
            403, "a token limited to a project or app cannot manage the organization"
        )


@router.get("/me")
def me(
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
) -> schemas.Me:
    org = caller.organization
    role = caller.role_in(org.id) if org else None
    project = (
        directory.project(org.id, caller.project_id)
        if org and caller.project_id
        else None
    )
    app = (
        directory.app(project.id, caller.app_id) if project and caller.app_id else None
    )

    return schemas.Me(
        user={
            "id": caller.user.id,
            "name": caller.user.name,
            "email": caller.user.email,
        },
        organization=org_dict(org) if org else None,
        organizations=[org_dict(o) for o, _ in caller.organizations]
        if caller.all_organizations
        else None,
        role=role,
        role_label=ROLE_LABELS.get(role, role) if role else None,
        scope=caller.scope,
        permissions=caller.permissions_in(org.id if org else None),
        token=caller.token_id,
        project=schemas.Named(id=project.id, name=project.name) if project else None,
        app=schemas.AppRef(id=app.id, name=app.name, registry_id=app.registry_id)
        if app
        else None,
    )


@router.get("/access")
def access(caller: Caller = Depends(get_caller)) -> schemas.AccessCatalog:
    return schemas.AccessCatalog(**catalog())


@router.get("/organizations")
def organizations(
    caller: Caller = Depends(get_caller),
) -> list[schemas.OrganizationRow]:
    return [
        schemas.OrganizationRow(
            id=o.id,
            name=o.name,
            slug=o.slug,
            role=role,
            role_label=ROLE_LABELS.get(role, role) if role else None,
            permissions=grants_of(role),
            grantable_scopes=grantable_scopes(role),
        )
        for o, role in caller.organizations
    ]


@router.post("/tokens", status_code=200)
def issue(
    body: schemas.IssueRequest,
    caller: Caller = Depends(get_caller),
    auth: AuthService = Depends(get_auth),
    directory: DirectoryService = Depends(get_directory),
) -> schemas.Issued:
    if caller.scope is not None or not caller.session_token:
        raise HTTPException(403, "a token cannot mint another token; sign in again")

    grant = Grant.parse(body.scope)

    if not grant.scope:
        raise HTTPException(
            400, "scope must include at least one of read, write, release, admin"
        )

    session = auth.require_session(caller.session_token)
    token, raw = auth.issue_token(
        session, grant, (body.name or "").strip()[:80] or "cli"
    )
    organization = (
        caller.member_of(token.organization_id) if token.organization_id else None
    )
    project = (
        directory.project(organization.id, token.project_id)
        if organization and token.project_id
        else None
    )
    app = directory.app(project.id, token.app_id) if project and token.app_id else None

    return schemas.Issued(
        token=raw,
        id=token.id,
        scope=Grant(
            parse_scopes(token.scope),
            token.organization_id or "*",
            token.project_id,
            token.app_id,
        ).format(),
        expires_at=token.expires_at,
        organization=org_dict(organization) if organization else None,
        organizations=None
        if organization
        else [org_dict(o) for o, _ in caller.organizations],
        project=schemas.Named(id=project.id, name=project.name) if project else None,
        app=schemas.AppRef(id=app.id, name=app.name, registry_id=app.registry_id)
        if app
        else None,
    )


def project_rows(
    directory: DirectoryService, caller: Caller, org: Organization, tag: bool
) -> list[schemas.ProjectRow]:
    rows = []

    for p in directory.projects_of(org.id, caller.project_id):
        team = directory.team(org.id, p.team_id) if p.team_id else None
        apps = directory.apps_of(p.id, caller.app_id)
        moments = [p.created_at] + [
            m for a in apps for m in (a.created_at, a.last_synced_at) if m
        ]
        rows.append(
            schemas.ProjectRow(
                id=p.id,
                name=p.name,
                slug=p.slug,
                description=p.description,
                team=schemas.Named(id=team.id, name=team.name) if team else None,
                apps=[
                    schemas.AppInProject(
                        id=a.id,
                        name=a.name,
                        registry_id=a.registry_id,
                        source_host_id=a.source_host_id,
                        last_synced_at=a.last_synced_at,
                    )
                    for a in apps
                ],
                organization=schemas.Named(id=org.id, name=org.name) if tag else None,
                created_at=p.created_at,
                updated_at=max(moments),
            )
        )

    return rows


@router.get("/projects")
def projects(
    x_organization: Optional[str] = Header(default=None),
    organization: Optional[str] = None,
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
) -> list[schemas.ProjectRow]:
    org = requested_org(caller, x_organization, organization)

    if org is None:
        return [
            row
            for o, _ in caller.organizations
            for row in project_rows(directory, caller, o, True)
        ]

    return project_rows(directory, caller, org, False)


@router.get("/teams")
def teams(
    x_organization: Optional[str] = Header(default=None),
    organization: Optional[str] = None,
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
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
                schemas.Named(id=p.id, name=p.name)
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


@router.post("/projects", status_code=201)
def create_project(
    body: schemas.CreateProjectRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
) -> schemas.Created:
    org = required_org(caller, x_organization, None)
    manageable(caller, org, "projects")
    project = directory.create_project(org.id, body.name, body.description or "")

    return schemas.Created(id=project.id, name=project.name, slug=project.slug)


@router.post("/teams", status_code=201)
def create_team(
    body: schemas.CreateTeamRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
) -> schemas.Created:
    org = required_org(caller, x_organization, None)
    manageable(caller, org, "teams")
    team = directory.create_team(org.id, body.name, body.description or "")

    return schemas.Created(id=team.id, name=team.name, slug=team.slug)


@router.post("/teams/members")
def add_team_member(
    body: schemas.TeamMemberRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
) -> schemas.Ok:
    org = required_org(caller, x_organization, None)
    manageable(caller, org, "teams/members")
    directory.add_team_member(org.id, body.team_id, body.user_id)

    return schemas.Ok()


@router.post("/projects/team")
def assign_project_team(
    body: schemas.ProjectTeamRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
) -> schemas.Ok:
    org = required_org(caller, x_organization, None)
    manageable(caller, org, "projects/team")
    directory.assign_project_team(org.id, body.project_id, body.team_id or None)

    return schemas.Ok()


@router.post("/members/role")
def set_member_role(
    body: schemas.MemberRoleRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
) -> schemas.Ok:
    org = required_org(caller, x_organization, None)
    manageable(caller, org, "members/role")
    directory.set_member_role(org.id, body.user_id, body.role)

    return schemas.Ok()


class JobOut(BaseModel):
    id: str
    kind: str
    status: str
    app_id: Optional[str] = None
    attempts: int
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    finished_at: Optional[datetime] = None


def get_queue(request: Request) -> JobQueue:
    if request.app.state.db is None:
        raise HTTPException(503, "no database configured: set AP_DATABASE_URL")

    return JobQueue(request.app.state.db)


@router.get("/jobs/{id}")
def job(
    id: str, caller: Caller = Depends(get_caller), queue: JobQueue = Depends(get_queue)
) -> JobOut:
    found = queue.get(id)

    if found is None or (
        found.organization_id and caller.member_of(found.organization_id) is None
    ):
        raise HTTPException(404, "no such job")

    return JobOut(**job_view(found))


@router.get("/jobs")
def jobs(
    app: str,
    caller: Caller = Depends(get_caller),
    directory: DirectoryService = Depends(get_directory),
    queue: JobQueue = Depends(get_queue),
) -> list[JobOut]:
    found = directory.app_by_registry_id(app)

    if (
        found is None
        or caller.member_of(found[1].organization_id) is None
        or not caller.within_reach(found[0].id, found[1].id)
    ):
        raise HTTPException(404, "app not found")

    return [JobOut(**job_view(j)) for j in queue.for_app(found[0].id)]
