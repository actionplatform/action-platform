from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from action_platform.api.access.caller import Caller
from action_platform.api.access.enrich import credentials_for
from action_platform.api.core.deps import get_app_service, get_db
from action_platform.api.db.models import Organization, PullRequest, Release
from action_platform.api.schemas import SourceCredentials
from action_platform.api.schemas import management as schemas
from action_platform.api.services.hosts import PROVIDERS, OAuthState
from action_platform.api.services.apps import AppService
from action_platform.api.services.directory import (
    DirectoryWrites,
)
from action_platform.api.services.activity import ActivityService
from action_platform.api.v1.routers.directory import get_caller, required_org
from action_platform.core.exception import ActionPlatformError
from action_platform.api.services.shared.urls import GitUrl

router = APIRouter(prefix="/api/v1", tags=["management"])


def get_writes(request: Request, db: DbSession = Depends(get_db)) -> DirectoryWrites:
    return DirectoryWrites(db, request.app.state.sealer)


def allowed(
    caller: Caller, org: Organization, permission: str, whole_org: bool = True
) -> None:
    ok, why = caller.allows(org.id, permission)

    if not ok:
        raise HTTPException(403, why)

    if whole_org and (caller.project_id or caller.app_id):
        raise HTTPException(
            403, "a token limited to a project or app cannot manage the organization"
        )


def org_of(caller: Caller, x_organization: Optional[str]) -> Organization:
    return required_org(caller, x_organization, None)


def host_row(host) -> schemas.HostRow:
    return schemas.HostRow(
        id=host.id,
        kind=host.kind,
        name=host.name,
        base_url=host.base_url,
        username=host.username,
        default_owner=host.default_owner,
        auth_kind=host.auth_kind,
        login=host.login,
        created_at=host.created_at,
    )


def imports_of(
    db: DbSession, app_id: str, errors: Optional[dict] = None
) -> schemas.Imports:
    releases = db.scalars(
        select(Release)
        .where(Release.app_id == app_id)
        .order_by(Release.published_at.desc())
    ).all()
    pulls = db.scalars(
        select(PullRequest)
        .where(PullRequest.app_id == app_id)
        .order_by(PullRequest.updated_at.desc())
    ).all()

    return schemas.Imports(
        releases=[
            schemas.ReleaseRow.model_validate(r, from_attributes=True) for r in releases
        ],
        pull_requests=[
            schemas.PullRequestRow.model_validate(p, from_attributes=True)
            for p in pulls
        ],
        errors=errors or {},
    )


def project_of(writes: DirectoryWrites, org: Organization, project_id: str):
    project = writes.project(org.id, project_id)

    if project is None:
        raise HTTPException(404, "project not found")

    return project


def app_of(writes: DirectoryWrites, caller: Caller, project, app_id: str):
    app = writes.app(project.id, app_id)

    if app is None or not caller.within_reach(app.id, project.id):
        raise HTTPException(404, "app not found")

    return app


def delete_remote(writes: DirectoryWrites, apps: AppService, org, app) -> Optional[str]:
    """Delete the repository behind `app` on its host; None when it was never pushed."""
    try:
        remote = apps.repository_of(app.registry_id)
    except ActionPlatformError:
        return None

    if remote is None:
        return None

    creds = writes.credentials_for(org.id, app.source_host_id)

    if creds is None:
        raise HTTPException(
            409,
            f"{app.name} lives on {remote[0]} but no connected host is attached to it; "
            "attach one in the app's settings or keep the repository",
        )

    return apps.delete_repository(app.registry_id, SourceCredentials(**creds.as_dict()))


@router.delete("/projects/{project_id}")
def delete_project(
    project_id: str,
    repositories: bool = False,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
    apps: AppService = Depends(get_app_service),
) -> schemas.Removed:
    org = org_of(caller, x_organization)
    allowed(caller, org, "project.manage")
    project = project_of(writes, org, project_id)
    project_apps = writes.apps_of(project.id)
    deleted = []

    if repositories:
        for app in project_apps:
            repo = delete_remote(writes, apps, org, app)

            if repo:
                deleted.append(repo)

    registry_ids = [a.registry_id for a in project_apps]

    for registry_id in registry_ids:
        try:
            apps.remove(registry_id)
        except ActionPlatformError:
            pass

    writes.delete_project(org.id, project_id)

    return schemas.Removed(removed=registry_ids, repositories=deleted)


@router.post("/projects/{project_id}/apps", status_code=201)
def add_app(
    project_id: str,
    body: schemas.AddAppToProject,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
    apps: AppService = Depends(get_app_service),
) -> schemas.AppAdded:
    org = org_of(caller, x_organization)
    allowed(caller, org, "project.manage")
    project = project_of(writes, org, project_id)
    url = body.url.strip()

    if not url:
        raise HTTPException(400, "url is required")

    host_id = writes.host_id_for_url(org.id, url)
    kind = GitUrl(url).kind

    if kind and host_id is None:
        raise HTTPException(
            400,
            f"No {kind} host is connected to this organization. Connect one in Settings so private repositories can be cloned.",
        )

    credentials = credentials_for(writes, org, None, {"url": url})
    entry = apps.add(url, None, SourceCredentials(**credentials), body.install)
    app = writes.create_app(project.id, entry["id"], entry["name"], host_id)
    ActivityService(writes.db).sync_all(
        app.id, writes.credentials_for(org.id, host_id), GitUrl(url).repo
    )

    return schemas.AppAdded(
        id=app.id,
        registry_id=app.registry_id,
        name=app.name,
        installed=entry.get("installed"),
    )


@router.post("/projects/{project_id}/apps/init", status_code=201)
def init_app(
    project_id: str,
    body: schemas.InitAppInProject,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
    apps: AppService = Depends(get_app_service),
) -> schemas.AppInitialized:
    org = org_of(caller, x_organization)
    allowed(caller, org, "project.manage")
    project = project_of(writes, org, project_id)
    creds = (
        writes.credentials_for(org.id, body.source_host_id)
        if body.source_host_id
        else None
    )

    if body.push and creds is None:
        raise HTTPException(400, "pushing needs a source host")

    name, email = writes.git_author_of(org.id)
    request = body.model_copy(
        update={
            "credentials": SourceCredentials(
                **{
                    **(creds.as_dict() if creds else {}),
                    "author_name": name,
                    "author_email": email,
                }
            ),
            "source": writes.source_spec_by_name(org.id, body.template_source),
        }
    )
    result = apps.init(request)
    app = writes.create_app(
        project.id, result["id"], result["name"], body.source_host_id
    )

    if result.get("pushed") and creds is not None:
        ActivityService(writes.db).sync_all(
            app.id, creds, GitUrl(result.get("url", "")).repo
        )

    return schemas.AppInitialized(
        id=app.id,
        registry_id=app.registry_id,
        name=app.name,
        pushed=bool(result.get("pushed")),
    )


@router.delete("/projects/{project_id}/apps/{app_id}")
def delete_app(
    project_id: str,
    app_id: str,
    repository: bool = False,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
    apps: AppService = Depends(get_app_service),
) -> schemas.Removed:
    org = org_of(caller, x_organization)
    allowed(caller, org, "project.manage")
    project = project_of(writes, org, project_id)
    app = writes.app(project.id, app_id)

    if app is None:
        return schemas.Removed()

    deleted = delete_remote(writes, apps, org, app) if repository else None

    try:
        apps.remove(app.registry_id)
    except ActionPlatformError:
        pass

    writes.delete_app(project.id, app_id)

    return schemas.Removed(
        removed=[app.registry_id], repositories=[deleted] if deleted else []
    )


@router.put("/projects/{project_id}/apps/{app_id}/host")
def set_app_host(
    project_id: str,
    app_id: str,
    body: schemas.AppHostRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.AppHostRequest:
    org = org_of(caller, x_organization)
    allowed(caller, org, "app.flow", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    if body.source_host_id and writes.host(org.id, body.source_host_id) is None:
        raise HTTPException(404, "host not found")

    writes.set_app_host(app, body.source_host_id or None)

    return schemas.AppHostRequest(source_host_id=app.source_host_id)


@router.get("/projects/{project_id}/apps/{app_id}/imports")
def imports(
    project_id: str,
    app_id: str,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.Imports:
    org = org_of(caller, x_organization)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)

    return imports_of(writes.db, app.id)


@router.post("/projects/{project_id}/apps/{app_id}/imports")
def sync_imports(
    project_id: str,
    app_id: str,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
    apps: AppService = Depends(get_app_service),
) -> schemas.Imports:
    org = org_of(caller, x_organization)
    allowed(caller, org, "app.sync", whole_org=False)
    project = project_of(writes, org, project_id)
    app = app_of(writes, caller, project, app_id)
    detail = apps.detail(app.registry_id)
    repo = (
        detail.get("source_host", {}).get("repo") or GitUrl(detail.get("url", "")).repo
    )

    if app.source_host_id is None:
        host_id = writes.host_id_for_url(org.id, detail.get("url", ""))

        if host_id:
            writes.set_app_host(app, host_id)

    errors = ActivityService(writes.db).sync_all(
        app.id, writes.credentials_for(org.id, app.source_host_id), repo
    )

    return imports_of(writes.db, app.id, errors)


@router.put("/teams/{team_id}")
def update_team(
    team_id: str,
    body: schemas.TeamUpdate,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> dict:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    team = writes.update_team(org.id, team_id, body.name, body.description or "")

    return {"id": team.id, "name": team.name, "slug": team.slug}


@router.delete("/teams/{team_id}", status_code=204)
def delete_team(
    team_id: str,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> None:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    writes.delete_team(org.id, team_id)


@router.delete("/teams/{team_id}/members/{user_id}", status_code=204)
def remove_team_member(
    team_id: str,
    user_id: str,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> None:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    writes.remove_team_member(org.id, team_id, user_id)


@router.delete("/members/{user_id}", status_code=204)
def remove_member(
    user_id: str,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> None:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    writes.remove_member(org.id, user_id)


@router.get("/invitations")
def invitations(
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> list[schemas.InvitationRow]:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")

    return [
        schemas.InvitationRow(
            id=i.id,
            email=i.email,
            role=i.role,
            status=i.status,
            expires_at=i.expires_at,
            created_at=i.created_at,
            inviter=u.name,
        )
        for i, u in writes.invitations_of(org.id)
    ]


@router.post("/invitations", status_code=201)
def invite(
    body: schemas.InviteRequest,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.InvitationRow:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    i = writes.create_invitation(org.id, caller.user.id, body.email, body.role)

    return schemas.InvitationRow(
        id=i.id,
        email=i.email,
        role=i.role,
        status=i.status,
        expires_at=i.expires_at,
        created_at=i.created_at,
        inviter=caller.user.name,
    )


@router.delete("/invitations/{id}", status_code=204)
def cancel_invitation(
    id: str,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> None:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    writes.cancel_invitation(org.id, id)


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


def state_signer(request: Request) -> OAuthState:
    return OAuthState(request.app.state.secrets)


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

    state = state_signer(request).sign(
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

    state = state_signer(request).verify(body.state, caller.user.id)
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

    state = state_signer(request).sign(
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
    state = state_signer(request).sign(org.id, return_to, caller.user.id)
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
    state = state_signer(request).verify(body.state, caller.user.id)

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


@router.get("/settings/git-author")
def git_author(
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.GitAuthor:
    org = org_of(caller, x_organization)
    name, email = writes.git_author_of(org.id)

    return schemas.GitAuthor(name=name, email=email)


@router.put("/settings/git-author")
def set_git_author(
    body: schemas.GitAuthor,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.GitAuthor:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    name, email = writes.set_git_author(org.id, body.name, body.email)

    return schemas.GitAuthor(name=name, email=email)


@router.get("/template-sources")
def template_sources(
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> list[schemas.TemplateSourceRow]:
    org = org_of(caller, x_organization)

    return [
        schemas.TemplateSourceRow.model_validate(r, from_attributes=True)
        for r in writes.template_sources_of(org.id)
    ]


@router.post("/template-sources", status_code=201)
def add_template_source(
    body: schemas.AddTemplateSource,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> schemas.TemplateSourceRow:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")

    return schemas.TemplateSourceRow.model_validate(
        writes.add_template_source(org.id, body.name, body.url, body.ref or ""),
        from_attributes=True,
    )


@router.delete("/template-sources/{id}", status_code=204)
def remove_template_source(
    id: str,
    x_organization: Optional[str] = Header(default=None),
    caller: Caller = Depends(get_caller),
    writes: DirectoryWrites = Depends(get_writes),
) -> None:
    org = org_of(caller, x_organization)
    allowed(caller, org, "org.manage")
    writes.remove_template_source(org.id, id)
