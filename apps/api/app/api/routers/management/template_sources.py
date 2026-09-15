"""Custom template repositories of the organization."""

from typing import Optional

from fastapi import APIRouter, Depends, Header

from app.services.access.caller import Caller
from app.schemas import management as schemas
from app.services.directory import (
    DirectoryWrites,
)

from app.api.dependencies import (
    allowed,
    get_caller,
    get_writes,
    org_of,
)

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/template-sources")
def template_sources(
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> list[schemas.TemplateSourceRow]:
    org = org_of(caller, x_organization)

    return [
        schemas.TemplateSourceRow.model_validate(r, from_attributes=True)
        for r in writes.template_sources_of(org.id)
    ]


@router.post("/template-sources", status_code=201)
def add_template_source(
    body: schemas.AddTemplateSource,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.TemplateSourceRow:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")

    return schemas.TemplateSourceRow.model_validate(
        writes.add_template_source(org.id, body.name, body.url, body.ref or ""),
        from_attributes=True,
    )


@router.delete("/template-sources/{id}", status_code=204)
def remove_template_source(
    id: str,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> None:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    writes.remove_template_source(org.id, id)
