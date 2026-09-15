"""The caller: who they are, what they may do, the organizations they belong to, and tokens for CLI and MCP."""

from fastapi import APIRouter, HTTPException

from action_platform.core.access import (
    ROLE_LABELS,
    Grant,
    catalog,
    grantable_scopes,
    grants_of,
    parse_scopes,
)
from app.api.dependencies import (
    AuthDep,
    CallerDep,
    DirectoryDep,
    org_dict,
)
from app.schemas import common
from app.schemas import organizations as schemas

router = APIRouter(prefix="/api/v1", tags=["identity"])


@router.get("/me")
def me(
    caller: CallerDep,
    directory: DirectoryDep,
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
        project=common.Named(id=project.id, name=project.name) if project else None,
        app=common.AppRef(id=app.id, name=app.name, registry_id=app.registry_id)
        if app
        else None,
    )


@router.get("/access")
def access(
    caller: CallerDep,
) -> schemas.AccessCatalog:
    return schemas.AccessCatalog(**catalog())


@router.get("/organizations")
def organizations(
    caller: CallerDep,
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
    caller: CallerDep,
    auth: AuthDep,
    directory: DirectoryDep,
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
        project=common.Named(id=project.id, name=project.name) if project else None,
        app=common.AppRef(id=app.id, name=app.name, registry_id=app.registry_id)
        if app
        else None,
    )
