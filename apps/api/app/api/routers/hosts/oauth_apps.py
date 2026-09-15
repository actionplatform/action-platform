"""The OAuth apps (client id and secret per provider) the platform connects hosts with."""

from typing import Optional

from fastapi import APIRouter, Depends, Header

from app.services.access.caller import Caller
from app.services.hosts import PROVIDERS
from app.services.directory import (
    DirectoryWrites,
)

from app.api.dependencies import (
    allowed,
    get_caller,
    get_writes,
    org_of,
)


from app.schemas import hosts as schemas

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/oauth/apps")
def oauth_apps(
    caller: Caller = Depends(get_caller), writes: DirectoryWrites = Depends(get_writes)
) -> list[schemas.OAuthAppRow]:
    rows = []

    for provider, app in writes.oauth_apps().items():
        host = PROVIDERS.get(provider)
        rows.append(
            schemas.OAuthAppRow(
                provider=provider,
                label=host.label,
                configured=app is not None,
                client_id=app.client_id if app else None,
                base_url=app.base_url if app else None,
                slug=app.slug if app else None,
                scopes=host.scopes,
                callback_hint=host.callback_hint,
            )
        )

    return rows


@router.put("/oauth/apps/{provider}", status_code=204)
def save_oauth_app(
    provider: str,
    body: schemas.OAuthAppRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> None:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    writes.save_oauth_app(provider, body.client_id, body.client_secret, body.base_url)


@router.delete("/oauth/apps/{provider}", status_code=204)
def clear_oauth_app(
    provider: str,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> None:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    writes.clear_oauth_app(provider)
