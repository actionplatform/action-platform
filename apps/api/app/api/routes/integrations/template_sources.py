"""Custom template repositories of the organization."""

from fastapi import APIRouter

from app.api.dependencies import (
    CallerDep,
    OrgDep,
    WritesDep,
    allowed,
)
from app.schemas import organizations as schemas

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/template-sources")
def template_sources(
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> list[schemas.TemplateSourceRow]:
    return [
        schemas.TemplateSourceRow.model_validate(r, from_attributes=True)
        for r in writes.template_sources_of(org.id)
    ]


@router.post("/template-sources", status_code=201)
def add_template_source(
    body: schemas.AddTemplateSource,
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> schemas.TemplateSourceRow:
    allowed(caller, org, "org.manage")

    return schemas.TemplateSourceRow.model_validate(
        writes.add_template_source(org.id, body.name, body.url, body.ref or ""),
        from_attributes=True,
    )


@router.delete("/template-sources/{id}", status_code=204)
def remove_template_source(
    id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> None:
    allowed(caller, org, "org.manage")
    writes.remove_template_source(org.id, id)
