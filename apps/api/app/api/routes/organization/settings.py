"""Organization settings."""

from typing import Optional

from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies import (
    CallerDep,
    DbDep,
    OrgDep,
    OrganizationRepoDep,
    QueueDep,
    allowed,
)
from app.core.errors import NotFound
from app.repositories.workspace.registry import Registry
from app.repositories.workspace.source import get_registry
from app.schemas import common
from app.schemas import organization as schemas
from app.services.access.job_dispatcher import JobDispatcher
from app.services.organization.removal import OrganizationRemoval

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/settings/git-author")
def git_author(
    org: OrgDep,
    caller: CallerDep,
    writes: OrganizationRepoDep,
) -> schemas.GitAuthor:
    name, email = writes.git_author_of(org.id)

    return schemas.GitAuthor(name=name, email=email)


@router.put("/settings/git-author")
def set_git_author(
    body: schemas.GitAuthor,
    org: OrgDep,
    caller: CallerDep,
    writes: OrganizationRepoDep,
) -> schemas.GitAuthor:
    allowed(caller, org, "org.manage")
    name, email = writes.set_git_author(org.id, body.name, body.email)

    return schemas.GitAuthor(name=name, email=email)


@router.delete("/organizations/{organization_id}")
def delete_organization(
    organization_id: str,
    request: Request,
    response: Response,
    org: OrgDep,
    caller: CallerDep,
    db: DbDep,
    queue: QueueDep,
    registry: Registry = Depends(get_registry),
    confirm: Optional[str] = None,
    repositories: bool = False,
    cloud: bool = False,
) -> common.Removed:
    """The organization leaves the platform with everything it owned. `confirm` must be its slug; only an owner may. `cloud` tears every app's deploy stacks down first, on the worker (202 with the job id)."""
    allowed(caller, org, "org.manage")
    target = caller.member_of(organization_id)

    if target is None or target.id != org.id:
        raise NotFound("no such organization")

    removal = OrganizationRemoval(db, request.app.state.sealer, registry)
    removal.check(org, caller.user.id, confirm)

    if cloud:
        response.status_code = 202

        return common.Removed(
            job=JobDispatcher(queue).destroy_organization(
                org, caller, repositories, confirm or ""
            )
        )

    result = removal.delete(org, caller.user.id, confirm, repositories)

    return common.Removed(
        removed=result["removed"], repositories=result["repositories"]
    )
