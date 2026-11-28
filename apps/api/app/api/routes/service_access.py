"""Access on the organization's services — GitHub, built in, and those the bundled plugins own — who, audit, sync, grant, revoke, offboard, and the read-only GitHub checks, for the caller's organization; every route needs `org.manage`, every change is a dry run unless `apply`."""

from typing import Optional

from fastapi import APIRouter, Request

from app.api.dependencies import CallerDep, OrgDep, OrganizationRepoDep, allowed
from app.schemas import service_access as schemas
from app.services.service_access import ServiceAccess

router = APIRouter(prefix="/api/v1/access", tags=["access"])


def _service(
    request: Request, org: OrgDep, caller: CallerDep, repo: OrganizationRepoDep
) -> ServiceAccess:
    allowed(caller, org, "org.manage")

    return ServiceAccess(
        request.app.state.db, request.app.state.sealer, repo, org.id, caller.user.id
    )


@router.get("/audit")
def audit(
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    repo: OrganizationRepoDep,
    service: Optional[str] = None,
) -> schemas.Audit:
    return _service(request, org, caller, repo).audit(service)


@router.get("/grants")
def grants(
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    repo: OrganizationRepoDep,
    person: Optional[str] = None,
    service: Optional[str] = None,
) -> schemas.Who:
    return _service(request, org, caller, repo).who(person, service)


@router.post("/syncs")
def run_sync(
    body: schemas.SyncRequest,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    repo: OrganizationRepoDep,
) -> schemas.Plan:
    return _service(request, org, caller, repo).sync(body)


@router.post("/people/{person}/grants")
def grant_person(
    person: str,
    body: schemas.PersonGrant,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    repo: OrganizationRepoDep,
) -> schemas.Plan:
    return _service(request, org, caller, repo).grant(
        schemas.GrantRequest(person=person, **body.model_dump())
    )


@router.delete("/people/{person}/grants/{service}/{resource:path}")
def revoke_person(
    person: str,
    service: str,
    resource: str,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    repo: OrganizationRepoDep,
    apply: bool = False,
) -> schemas.Plan:
    return _service(request, org, caller, repo).revoke(
        schemas.RevokeRequest(
            person=person, service=service, resource=resource, apply=apply
        )
    )


@router.delete("/people/{person}")
def offboard_person(
    person: str,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    repo: OrganizationRepoDep,
    apply: bool = False,
    remove_from_platform: bool = False,
) -> schemas.Plan:
    return _service(request, org, caller, repo).offboard(
        schemas.OffboardRequest(
            person=person, apply=apply, remove_from_platform=remove_from_platform
        )
    )


@router.get("/who", include_in_schema=False)
def who(
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    repo: OrganizationRepoDep,
    person: Optional[str] = None,
    service: Optional[str] = None,
) -> schemas.Who:
    return _service(request, org, caller, repo).who(person, service)


@router.post("/sync", include_in_schema=False)
def sync(
    body: schemas.SyncRequest,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    repo: OrganizationRepoDep,
) -> schemas.Plan:
    return _service(request, org, caller, repo).sync(body)


@router.post("/grant", include_in_schema=False)
def grant(
    body: schemas.GrantRequest,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    repo: OrganizationRepoDep,
) -> schemas.Plan:
    return _service(request, org, caller, repo).grant(body)


@router.post("/revoke", include_in_schema=False)
def revoke(
    body: schemas.RevokeRequest,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    repo: OrganizationRepoDep,
) -> schemas.Plan:
    return _service(request, org, caller, repo).revoke(body)


@router.post("/offboard", include_in_schema=False)
def offboard(
    body: schemas.OffboardRequest,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    repo: OrganizationRepoDep,
) -> schemas.Plan:
    return _service(request, org, caller, repo).offboard(body)


@router.get("/github/branch-protection")
def github_branch_protection(
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    directory: OrganizationRepoDep,
    repo: Optional[str] = None,
) -> schemas.BranchProtection:
    return _service(request, org, caller, directory).github_branch_protection(repo)


@router.get("/github/repo-settings")
def github_repo_settings(
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    directory: OrganizationRepoDep,
    repo: Optional[str] = None,
) -> schemas.OrgSettings:
    return _service(request, org, caller, directory).github_repo_settings(repo)
