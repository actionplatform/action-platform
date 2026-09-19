"""GitHub Apps: created from a manifest, installed on an account."""

import re

from fastapi import APIRouter, HTTPException, Request

from app.api.dependencies import (
    CallerDep,
    OrgDep,
    IntegrationsDep,
    allowed,
    get_state_signer,
)
from app.schemas import integrations as schemas
from app.services.integrations.hosts import PROVIDERS, HostConnector

GITHUB_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")

router = APIRouter(prefix="/api/v1", tags=["management"])


@router.post("/oauth/github/install")
def github_install(
    body: schemas.OAuthStartRequest,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    writes: IntegrationsDep,
) -> schemas.OAuthStarted:
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
    body: schemas.GitHubAppManifestRequest,
    request: Request,
    org: OrgDep,
    caller: CallerDep,
    writes: IntegrationsDep,
) -> schemas.Manifest:
    allowed(caller, org, "org.manage")

    if writes.oauth_app("github") is not None:
        raise HTTPException(409, "a GitHub app is already configured")

    return_to = body.return_to or "/settings"
    state = get_state_signer(request).sign(org.id, return_to, caller.user.id)
    github_org = (body.github_org or "").strip()

    if github_org and not GITHUB_LOGIN.match(github_org):
        raise HTTPException(400, "github_org must be a GitHub organization login")

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
    caller: CallerDep,
    writes: IntegrationsDep,
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

    slug, problem = HostConnector(writes).create_github_app(body.code)

    if problem:
        return schemas.OAuthFinished(
            return_to=state["returnTo"], query={"oauth_error": problem}
        )

    return schemas.OAuthFinished(
        return_to=state["returnTo"], query={"github_app": slug}
    )
