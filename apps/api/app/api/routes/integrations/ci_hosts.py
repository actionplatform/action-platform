"""CI servers connected to the organization."""

from fastapi import APIRouter

from action_platform.core.exception import ActionPlatformError
from action_platform.providers.ci import build_ci_runner
from app.api.dependencies import CallerDep, IntegrationsDep, OrgDep, allowed
from app.schemas import ci as schemas

router = APIRouter(prefix="/api/v1", tags=["management"])


def ci_host_row(host) -> schemas.CiHostRow:
    return schemas.CiHostRow(
        id=host.id,
        kind=host.kind,
        name=host.name,
        base_url=host.base_url,
        username=host.username,
        created_at=host.created_at,
    )


@router.get("/ci-hosts")
def ci_hosts(
    org: OrgDep,
    caller: CallerDep,
    writes: IntegrationsDep,
) -> list[schemas.CiHostRow]:
    return [ci_host_row(h) for h in writes.ci_hosts_of(org.id)]


@router.post("/ci-hosts", status_code=201)
def add_ci_host(
    body: schemas.AddCiHostRequest,
    org: OrgDep,
    caller: CallerDep,
    writes: IntegrationsDep,
) -> schemas.CiHostRow:
    allowed(caller, org, "org.manage")

    return ci_host_row(
        writes.add_ci_host(
            org.id,
            body.kind,
            body.name or "",
            body.base_url,
            body.token,
            body.username,
        )
    )


@router.delete("/ci-hosts/{host_id}", status_code=204)
def remove_ci_host(
    host_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: IntegrationsDep,
) -> None:
    allowed(caller, org, "org.manage")
    writes.remove_ci_host(org.id, host_id)


@router.post("/ci-hosts/{host_id}/test")
def test_ci_host(
    host_id: str,
    org: OrgDep,
    caller: CallerDep,
    writes: IntegrationsDep,
) -> dict:
    creds = writes.ci_credentials_for(org.id, host_id)

    if creds is None:
        return {"ok": False, "error": "ci host not found"}

    try:
        build_ci_runner(
            creds.kind,
            base_url=creds.base_url,
            token=creds.token,
            username=creds.username,
        ).test()
    except ActionPlatformError as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "error": None}
