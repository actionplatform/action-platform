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


@router.get("/who")
def who(
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    repo: OrganizationRepoDep,
    person: Optional[str] = None,
    service: Optional[str] = None,
) -> schemas.Who:
    return _service(request, org, caller, repo).who(person, service)


@router.post("/sync")
def sync(
    body: schemas.SyncRequest,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    repo: OrganizationRepoDep,
) -> schemas.Plan:
    return _service(request, org, caller, repo).sync(body)


@router.post("/grant")
def grant(
    body: schemas.GrantRequest,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    repo: OrganizationRepoDep,
) -> schemas.Plan:
    return _service(request, org, caller, repo).grant(body)


@router.post("/revoke")
def revoke(
    body: schemas.RevokeRequest,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    repo: OrganizationRepoDep,
) -> schemas.Plan:
    return _service(request, org, caller, repo).revoke(body)


@router.post("/offboard")
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
