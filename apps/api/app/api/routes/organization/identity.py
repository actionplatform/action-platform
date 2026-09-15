"""The caller: who they are, what they may do, the organizations they belong to, and tokens for CLI and MCP."""

from fastapi import APIRouter

from action_platform.core.access import (
    ROLE_LABELS,
    catalog,
    grantable_scopes,
    grants_of,
)
from app.api.dependencies import (
    AuthDep,
    CallerDep,
    DirectoryDep,
    org_dict,
)
from app.schemas import common
from app.schemas import organizations as schemas

from app.services.organization.sessions import TokenMinter

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
    minted = TokenMinter(auth, directory).mint(caller, body.scope, body.name)
    organization, project, app = minted.organization, minted.project, minted.app

    return schemas.Issued(
        token=minted.raw,
        id=minted.token.id,
        scope=minted.scope,
        expires_at=minted.token.expires_at,
        organization=org_dict(organization) if organization else None,
        organizations=None
        if organization
        else [org_dict(o) for o, _ in caller.organizations],
        project=common.Named(id=project.id, name=project.name) if project else None,
        app=common.AppRef(id=app.id, name=app.name, registry_id=app.registry_id)
        if app
        else None,
    )
