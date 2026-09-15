"""GitHub Apps: created from a manifest, installed on an account."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.services.access.caller import Caller
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


from app.schemas import hosts as schemas

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.post("/oauth/github/install")
def github_install(
    body: schemas.OAuthStartRequest,
    request: Request,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.OAuthStarted:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    app = writes.oauth_app("github")

    if app is None or not app.slug:
        raise HTTPException(400, "GitHub App is not configured")

    state = get_state_signer(request).sign(
        org.id, body.return_to or "/settings", caller.user.id
    )

    return schemas.OAuthStarted(
        url=f"https://github.com/apps/{app.slug}/installations/select_target?state={state}"
    )


@router.post("/oauth/github/manifest")
def github_manifest(
    body: schemas.ManifestRequest,
    request: Request,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.Manifest:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")

    if writes.oauth_app("github") is not None:
        raise HTTPException(409, "a GitHub app is already configured")

    return_to = body.return_to or "/settings"
    state = get_state_signer(request).sign(org.id, return_to, caller.user.id)
    github_org = (body.github_org or "").strip()
    target = (
        f"https://github.com/organizations/{github_org}/settings/apps/new"
        if github_org
        else "https://github.com/settings/apps/new"
    )

    return schemas.Manifest(
        target=f"{target}?state={state}",
        state=state,
        manifest=PROVIDERS.github.manifest(
            body.origin.rstrip("/"), body.host, return_to
        ),
    )


@router.post("/oauth/github/manifest/callback")
def github_manifest_callback(
    body: schemas.ManifestCallbackRequest,
    request: Request,
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.OAuthFinished:
    state = get_state_signer(request).verify(body.state, caller.user.id)

    if state is None:
        raise HTTPException(400, "invalid or expired state")

    org = caller.member_of(state["orgId"])

    if org is None:
        raise HTTPException(403, "no organization")

    allowed(caller, org, "org.manage")

    if not body.code:
        return schemas.OAuthFinished(
            return_to=state["returnTo"], query={"oauth_error": "GitHub sent no code"}
        )

    try:
        app = PROVIDERS.github.convert_manifest(body.code)
    except ActionPlatformError as e:
        return schemas.OAuthFinished(
            return_to=state["returnTo"], query={"oauth_error": str(e)}
        )

    writes.save_oauth_app(
        "github", app["client_id"], app["client_secret"], None, app.get("slug")
    )

    return schemas.OAuthFinished(
        return_to=state["returnTo"], query={"github_app": app.get("slug") or "created"}
    )
