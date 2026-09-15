"""Code hosts connected to the organization."""

from typing import Optional

from fastapi import APIRouter, Depends, Header

from app.services.access.caller import Caller
from app.services.hosts import PROVIDERS
from app.services.directory import (
    DirectoryWrites,
)
from action_platform.core.exception import ActionPlatformError

from app.api.dependencies import (
    allowed,
    get_caller,
    get_writes,
    host_row,
    org_of,
)

from app.schemas import hosts as schemas

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/hosts")
def hosts(
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> list[schemas.HostRow]:
    org = org_of(caller, x_organization)

    return [host_row(h) for h in writes.hosts_of(org.id)]


@router.post("/hosts", status_code=201)
def add_host(
    body: schemas.AddHostRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.HostRow:
    org = org_of(caller, x_organization)
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
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> None:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    writes.remove_host(org.id, host_id)


@router.put("/hosts/{host_id}/token", status_code=204)
def rotate_host_token(
    host_id: str,
    body: schemas.HostTokenRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> None:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    writes.update_host_token(org.id, host_id, body.token)


@router.put("/hosts/{host_id}/owner", status_code=204)
def set_host_owner(
    host_id: str,
    body: schemas.HostOwnerRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> None:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    writes.set_host_owner(org.id, host_id, body.owner)


@router.get("/hosts/{host_id}/access")
def host_access(
    host_id: str,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> dict:
    org = org_of(caller, x_organization)

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
