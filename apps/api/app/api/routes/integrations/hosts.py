"""Code hosts connected to the organization."""

from fastapi import APIRouter

from action_platform.core.exception import ActionPlatformError
from app.api.dependencies import (
    CallerDep,
    OrgDep,
    WritesDep,
    allowed,
    host_row,
)
from app.schemas import hosts as schemas
from app.services.hosts import PROVIDERS

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/hosts")
def hosts(
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> list[schemas.HostRow]:
    return [host_row(h) for h in writes.hosts_of(org.id)]


@router.post("/hosts", status_code=201)
def add_host(
    body: schemas.AddHostRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> schemas.HostRow:
    allowed(caller, org, "org.manage")

    return host_row(
        writes.add_host(
            org.id,
            body.kind,
            body.name or "",
            body.token,
            body.base_url,
            body.username,
            body.default_owner,
        )
    )


@router.delete("/hosts/{host_id}", status_code=204)
def remove_host(
    host_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> None:
    allowed(caller, org, "org.manage")
    writes.remove_host(org.id, host_id)


@router.put("/hosts/{host_id}/token", status_code=204)
def rotate_host_token(
    host_id: str,
    body: schemas.HostTokenRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> None:
    allowed(caller, org, "org.manage")
    writes.update_host_token(org.id, host_id, body.token)


@router.put("/hosts/{host_id}/owner", status_code=204)
def set_host_owner(
    host_id: str,
    body: schemas.HostOwnerRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> None:
    allowed(caller, org, "org.manage")
    writes.set_host_owner(org.id, host_id, body.owner)


@router.get("/hosts/{host_id}/access")
def host_access(
    host_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> dict:
    try:
        creds = writes.credentials_for(org.id, host_id)
    except ActionPlatformError as e:
        return {"ok": False, "error": f"{e}; reconnect the host"}

    if creds is None:
        return {"ok": False, "error": "no credentials"}

    github = writes.oauth_app("github")

    try:
        access = PROVIDERS.get(creds.kind).access(
            creds, github.slug if github else None
        )
    except ActionPlatformError as e:
        return {"ok": False, "error": str(e)}

    if creds.kind == "bitbucket" and access.get("ok") and access["installations"]:
        slugs = [i["account"] for i in access["installations"]]

        if not creds.owner or creds.owner not in slugs:
            first = next(
                (i for i in access["installations"] if i["canCreateRepos"]),
                access["installations"][0],
            )
            writes.set_host_owner(org.id, host_id, first["account"])

    return access
