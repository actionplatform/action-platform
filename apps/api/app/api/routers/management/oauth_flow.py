"""Connecting a host with OAuth: start, callback, disconnect."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.services.access.caller import Caller
from app.schemas import management as schemas
from app.services.hosts import PROVIDERS
from app.services.directory import (
    DirectoryWrites,
)
from action_platform.core.exception import ActionPlatformError

from app.api.dependencies import (
    get_state_signer,
    allowed,
    get_caller,
    get_writes,
    org_of,
)


router = APIRouter(prefix="/api/v1", tags=["management"])


@router.post("/oauth/{provider}/start")
def oauth_start(
    provider: str,
    body: schemas.OAuthStartRequest,
    request: Request,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.OAuthStarted:
    if provider not in PROVIDERS.by_kind:
        raise HTTPException(404, "unknown provider")

    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    app = writes.oauth_app(provider)

    if app is None:
        raise HTTPException(
            400, f"{PROVIDERS.get(provider).label} OAuth app is not configured"
        )

    state = get_state_signer(request).sign(
        org.id, body.return_to or "/settings", caller.user.id
    )

    return schemas.OAuthStarted(
        url=PROVIDERS.get(provider).authorize_url(app, body.origin.rstrip("/"), state)
    )


@router.post("/oauth/{provider}/callback")
def oauth_callback(
    provider: str,
    body: schemas.OAuthCallbackRequest,
    request: Request,
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.OAuthFinished:
    if provider not in PROVIDERS.by_kind:
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

    app = writes.oauth_app(provider)

    if app is None:
        return schemas.OAuthFinished(
            return_to=return_to,
            query={
                "oauth_error": f"{PROVIDERS.get(provider).label} OAuth app is not configured"
            },
        )

    try:
        host = PROVIDERS.get(provider)
        access, refresh, expires_at = host.exchange_code(
            app, body.origin.rstrip("/"), body.code
        )
        login, _ = host.identity(app, access)
        owner = (
            PROVIDERS.github.installation_owner(access, body.installation_id)
            if body.installation_id
            else PROVIDERS.bitbucket.first_workspace(access)
            if provider == "bitbucket"
            else None
        )
        writes.connect_oauth_host(
            org.id,
            provider,
            login,
            access,
            refresh,
            expires_at,
            host.stored_base_url(app),
            owner,
        )
    except ActionPlatformError as e:
        return schemas.OAuthFinished(return_to=return_to, query={"oauth_error": str(e)})

    return schemas.OAuthFinished(return_to=return_to, query={"connected": provider})


@router.delete("/oauth/{provider}/hosts/{login}", status_code=204)
def disconnect_oauth_host(
    provider: str,
    login: str,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> None:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    writes.remove_oauth_host(org.id, provider, login)
