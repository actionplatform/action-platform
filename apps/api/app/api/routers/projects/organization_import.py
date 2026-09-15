"""Importing a whole organization from a code host: what it shows, and the job that brings it in."""

from fastapi import APIRouter

from app.api.dependencies import CallerDep, ImportsDep, OrgDep, allowed
from app.schemas import imports as schemas

router = APIRouter(prefix="/api/v1/import", tags=["import"])


@router.get("/github/organizations")
def github_organizations(
    host: str, org: OrgDep, caller: CallerDep, imports: ImportsDep
) -> schemas.GithubOrganizations:
    allowed(caller, org, "org.manage")
    rows, install_url = imports.organizations(org, host)

    return schemas.GithubOrganizations(organizations=rows, install_url=install_url)


@router.get("/github/organizations/{login}")
def github_organization(
    login: str,
    host: str,
    org: OrgDep,
    caller: CallerDep,
    imports: ImportsDep,
) -> schemas.GithubPreview:
    allowed(caller, org, "org.manage")

    return imports.preview(org, host, login)


@router.post("/github", status_code=202)
def import_github(
    body: schemas.ImportRequest,
    org: OrgDep,
    caller: CallerDep,
    imports: ImportsDep,
) -> schemas.ImportQueued:
    allowed(caller, org, "org.manage")
    job = imports.enqueue(org, caller.user.id, body.model_dump())

    return schemas.ImportQueued(job=job.id, poll=f"/api/v1/jobs/{job.id}")
