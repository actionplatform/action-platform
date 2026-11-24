"""Services the organization connected with OAuth that are not code hosts (Sentry): which, with what scopes, and disconnecting one. Connecting goes through `/oauth/{kind}/start`."""

from fastapi import APIRouter, HTTPException

from app.api.dependencies import (
    CallerDep,
    ConnectionProvidersDep,
    IntegrationsDep,
    OrgDep,
    allowed,
)
from app.schemas import integrations as schemas
from app.services.integrations.hosts.scopes import scopes_for

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/connections")
def connections(
    org: OrgDep,
    caller: CallerDep,
    writes: IntegrationsDep,
    services: ConnectionProvidersDep,
) -> list[schemas.ConnectionRow]:
    rows = {r.kind: r for r in writes.connections_of(org.id)}
    out = []

    for provider in services:
        row = rows.get(provider.kind)
        asked = scopes_for(provider.kind, provider.scopes).split()
        granted = row.scopes.split() if row and row.scopes is not None else None
        out.append(
            schemas.ConnectionRow(
                kind=provider.kind,
                label=provider.label,
                configured=writes.oauth_app(provider.kind) is not None,
                connected=row is not None,
                login=row.login if row else None,
                base_url=row.base_url if row else None,
                scopes=granted,
                asked=asked,
                missing=[s for s in asked if s not in granted]
                if granted is not None
                else [],
                expires_at=row.expires_at if row else None,
                connected_at=row.created_at if row else None,
            )
        )

    return out


@router.delete("/connections/{kind}", status_code=204)
def disconnect(
    kind: str,
    org: OrgDep,
    caller: CallerDep,
    writes: IntegrationsDep,
    services: ConnectionProvidersDep,
) -> None:
    if kind not in services:
        raise HTTPException(404, "unknown service")

    allowed(caller, org, "org.manage")
    writes.remove_connection(org.id, kind)
