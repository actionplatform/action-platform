"""Connecting a host with OAuth: start, callback, disconnect."""

from fastapi import APIRouter, HTTPException, Request

from app.api.dependencies import (
    CallerDep,
    HostProvidersDep,
    OrgDep,
    IntegrationsDep,
    allowed,
    get_state_signer,
)
from app.schemas import integrations as schemas
from app.services.integrations.hosts import HostConnectError, HostConnector

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.post("/oauth/{provider}/start")
def oauth_start(
    provider: str,
    body: schemas.OAuthStartRequest,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    writes: IntegrationsDep,
    providers: HostProvidersDep,
) -> schemas.OAuthStarted:
    if provider not in providers:
        raise HTTPException(404, "unknown provider")

    allowed(caller, org, "org.manage")
    app = writes.oauth_app(provider)

    if app is None:
        raise HTTPException(
            400, f"{providers.get(provider).label} OAuth app is not configured"
        )

    state = get_state_signer(request).sign(
        org.id, body.return_to or "/settings", caller.user.id
    )

    return schemas.OAuthStarted(
        url=providers.get(provider).authorize_url(app, body.origin.rstrip("/"), state)
    )


@router.post("/oauth/{provider}/callback")
def oauth_callback(
    provider: str,
    body: schemas.OAuthCallbackRequest,
    request: Request,
    caller: CallerDep,
    writes: IntegrationsDep,
    providers: HostProvidersDep,
) -> schemas.OAuthFinished:
    if provider not in providers:
        raise HTTPException(404, "unknown provider")

    state = get_state_signer(request).verify(body.state, caller.user.id)
    installed = provider == "github" and bool(body.installation_id)

    if state is None and not installed:
        raise HTTPException(400, "invalid or expired state")

    if state is not None:
        org = caller.member_of(state["orgId"])

        return_to = state["returnTo"]
    else:
        org = caller.organization

        return_to = "/settings"

    if org is None:
        raise HTTPException(403, "no organization")

    allowed(caller, org, "org.manage")

    if body.error:
        return schemas.OAuthFinished(
            return_to=return_to,
            query={"oauth_error": body.error_description or body.error},
        )

    if not body.code:
        return schemas.OAuthFinished(
            return_to=return_to, query={"oauth_error": "no code from the provider"}
        )

    try:
        HostConnector(writes, providers).finish(
            org, provider, body.origin.rstrip("/"), body.code, body.installation_id
        )
    except HostConnectError as e:
        return schemas.OAuthFinished(return_to=return_to, query={"oauth_error": str(e)})

    return schemas.OAuthFinished(return_to=return_to, query={"connected": provider})


@router.delete("/oauth/{provider}/hosts/{login}", status_code=204)
def disconnect_oauth_host(
    provider: str,
    login: str,
    org: OrgDep,
    caller: CallerDep,
    writes: IntegrationsDep,
) -> None:
    allowed(caller, org, "org.manage")
    writes.remove_oauth_host(org.id, provider, login)
