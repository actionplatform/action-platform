"""The OAuth apps (client id and secret per provider) the platform connects hosts with."""

from fastapi import APIRouter

from app.api.dependencies import (
    CallerDep,
    OrgDep,
    WritesDep,
    allowed,
)
from app.schemas import hosts as schemas
from app.services.integrations.hosts import PROVIDERS

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.get("/oauth/apps")
def oauth_apps(
    caller: CallerDep,
    writes: WritesDep,
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
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> None:
    allowed(caller, org, "org.manage")
    writes.save_oauth_app(provider, body.client_id, body.client_secret, body.base_url)


@router.delete("/oauth/apps/{provider}", status_code=204)
def clear_oauth_app(
    provider: str,
    org: OrgDep,
    caller: CallerDep,
    writes: WritesDep,
) -> None:
    allowed(caller, org, "org.manage")
    writes.clear_oauth_app(provider)
