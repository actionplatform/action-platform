"""Importing a whole organization from a code host (GitHub, GitLab, Bitbucket): what it shows, and the job that brings it in."""

from fastapi import APIRouter

from app.api.dependencies import CallerDep, ImportsDep, OrgDep, allowed
from app.schemas import organization_import as schemas

router = APIRouter(prefix="/api/v1/import", tags=["import"])


def _organizations(
    host: str, org: OrgDep, caller: CallerDep, imports: ImportsDep
) -> schemas.ImportOrganizations:
    allowed(caller, org, "org.manage")
    rows, install_url = imports.organizations(org, host)

    return schemas.ImportOrganizations(organizations=rows, install_url=install_url)


def _preview(
    host: str, login: str, org: OrgDep, caller: CallerDep, imports: ImportsDep
) -> schemas.ImportPreview:
    allowed(caller, org, "org.manage")

    return imports.preview(org, host, login)


def _enqueue(
    body: schemas.ImportRequest, org: OrgDep, caller: CallerDep, imports: ImportsDep
) -> schemas.ImportQueued:
    allowed(caller, org, "org.manage")
    job = imports.enqueue(org, caller.user.id, body.model_dump())

    return schemas.ImportQueued(job=job.id, poll=f"/api/v1/jobs/{job.id}")


@router.get("/github/organizations")
def github_organizations(
    host: str, org: OrgDep, caller: CallerDep, imports: ImportsDep
) -> schemas.ImportOrganizations:
    return _organizations(host, org, caller, imports)


@router.get("/github/organizations/{login}")
def github_organization(
    login: str,
    host: str,
    org: OrgDep,
    caller: CallerDep,
    imports: ImportsDep,
) -> schemas.ImportPreview:
    return _preview(host, login, org, caller, imports)


@router.post("/github", status_code=202)
def import_github(
    body: schemas.ImportRequest,
    org: OrgDep,
    caller: CallerDep,
    imports: ImportsDep,
) -> schemas.ImportQueued:
    return _enqueue(body, org, caller, imports)


@router.get("/{host_id}/organizations")
def organizations(
    host_id: str, org: OrgDep, caller: CallerDep, imports: ImportsDep
) -> schemas.ImportOrganizations:
    return _organizations(host_id, org, caller, imports)


@router.get("/{host_id}/organizations/{login:path}")
def organization(
    host_id: str,
    login: str,
    org: OrgDep,
    caller: CallerDep,
    imports: ImportsDep,
) -> schemas.ImportPreview:
    return _preview(host_id, login, org, caller, imports)


@router.post("", status_code=202)
def import_organization(
    body: schemas.ImportRequest,
    org: OrgDep,
    caller: CallerDep,
    imports: ImportsDep,
) -> schemas.ImportQueued:
    return _enqueue(body, org, caller, imports)
