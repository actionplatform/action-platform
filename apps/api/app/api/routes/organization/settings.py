"""Organization settings."""

from fastapi import APIRouter

from app.api.dependencies import (
    CallerDep,
    OrgDep,
    WritesDep,
    allowed,
)
from app.schemas import organizations as schemas

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/settings/git-author")
def git_author(
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> schemas.GitAuthor:
    name, email = writes.git_author_of(org.id)

    return schemas.GitAuthor(name=name, email=email)


@router.put("/settings/git-author")
def set_git_author(
    body: schemas.GitAuthor,
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> schemas.GitAuthor:
    allowed(caller, org, "org.manage")
    name, email = writes.set_git_author(org.id, body.name, body.email)

    return schemas.GitAuthor(name=name, email=email)
