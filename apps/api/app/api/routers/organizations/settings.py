"""Organization settings."""

from typing import Optional

from fastapi import APIRouter, Depends, Header

from app.services.access.caller import Caller
from app.services.directory import (
    DirectoryWrites,
)

from app.api.dependencies import (
    allowed,
    get_caller,
    get_writes,
    org_of,
)

from app.schemas import organizations as schemas

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/settings/git-author")
def git_author(
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.GitAuthor:
    org = org_of(caller, x_organization)
    name, email = writes.git_author_of(org.id)

    return schemas.GitAuthor(name=name, email=email)


@router.put("/settings/git-author")
def set_git_author(
    body: schemas.GitAuthor,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.GitAuthor:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    name, email = writes.set_git_author(org.id, body.name, body.email)

    return schemas.GitAuthor(name=name, email=email)
