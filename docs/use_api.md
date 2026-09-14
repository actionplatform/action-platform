# API

`action-platform api` — the JSON API the web app drives; a FastAPI process listening on `:7788` with OpenAPI at `/docs`. It is released as its own component (`api/vX.Y.Z`, image `actionplatformio/action-platform-api`) and reports that version in `GET /api/version`.

`action-platform api` — one process. Workspaces are file-backed under `AP_HOME`; accounts, sessions, organizations and tokens live in the [database](concept_database.md) the API owns. Which project or app a caller may touch is still checked by the web app's `/api/v1` proxy; that moves here next.

| Endpoint | |
|---|---|
| `GET /api/version` (`{version, api}`), `GET /api/matrix`, `POST /api/matrix {sources}`, `GET /api/gitflow/rules` | static; `POST /matrix` merges extra template repositories |
| `GET /api/apps`, `POST /api/apps {url, name, install}`, `POST /api/apps/init`, `DELETE /api/apps/{id}` | registry: clone a repository (installing the platform when asked), generate from a template, remove the workspace |
| `POST /api/apps/{id}/sync {reset}`, `/push {private}` | fetch + fast-forward (stash around it, follow a rewritten remote, leave a merged branch); create the remote and push |
| `GET /api/apps/{id}`, `/gitflow`, `/commits`, `/branches`, `/tags`, `/releases`, `/changes` | state of the workspace; a clone that lost `platform.toml` gets it back on the spot |
| `GET/PUT /api/apps/{id}/manifest`, `POST /cloud`, `/services`, `/install`, `/discard`, `/commit {message, branch, push, pull_request}` | configuration: edit platform.toml, apply overlays, reinstall, drop or commit the changes (on a new git-flow branch with a pull request when the branch is protected) |
| `POST /api/apps/{id}/branches`, `/checkout`, `GET/POST /pull-request` | git-flow: start a branch, switch, propose and open a pull request |
| `POST /api/apps/{id}/release {level, branch, dry_run}`, `/deploy`, `GET /diagnose` | release (fast-forwarded first; a refused push undoes commit and tag), deploy, diagnose; `dry_run` defaults to true |

## Auth

`/api/auth/*` is where accounts live; the web app is a client of it and sets the browser cookie the API signs.

| Endpoint | |
|---|---|
| `GET /api/auth/status` | `{configured, users}` — whether `AP_AUTH_SECRET` is set and anyone has signed up |
| `POST /api/auth/sign-up {name, email, password, invitation_id}` | open for the first account only; afterwards needs a pending invitation for that email. Answers user + session (`token`, signed `cookie`, `expires_at`) |
| `POST /api/auth/sign-in {email, password, ip_address, user_agent}`, `POST /sign-out` | password checked with the same scrypt parameters the web app used, so every existing account keeps working; 10 attempts per minute per IP |
| `GET /api/auth/session` | who the caller is: user, session, active organization, every organization, role and its grants. The caller identifies with `X-Session-Token` (raw) or `X-Session-Cookie` (the signed cookie value) |
| `POST /api/auth/session/organization {organization_id}`, `GET /sessions`, `DELETE /sessions/{id}` | switch organization (members only), list and revoke browser sessions |
| `POST /api/auth/organizations {name, slug, git_author_name, git_author_email}`, `POST /members {organization_id, name, email, password, role}` | create an organization (caller becomes owner, it becomes active); add a member with a password (owners and admins) |
| `POST /api/auth/device/code {client_id, scope}`, `POST /device/token {grant_type, device_code}` | RFC 8628 for the CLI: `authorization_pending`, `slow_down`, `access_denied`, `expired_token` as `{error, error_description}`; an approved code becomes a session token |
| `GET /api/auth/device?user_code=`, `POST /device/approve {user_code, grant}`, `POST /device/deny` | the browser side: what the device asked, then approve with a grant cut to the caller's role, or deny |
| `POST /api/auth/tokens {name, scope, organization_id, project_id, app_id}`, `GET /tokens`, `DELETE /tokens/{id}`, `POST /tokens/verify {token, client}` | scoped JWTs ([access control](concept_access_control.md)); `verify` answers the claims plus organizations and role, and records the client program |

Sessions last 7 days, refreshed when used after a day. Refusals answer `{"detail", "error", "error_description"}` with `401` (`unauthenticated`, `invalid_credentials`), `403` (`forbidden`), `409` (`exists`), `429` (rate limit) or `400` for the rest.

Every response is a Pydantic model under `api/schemas/`; `apps/web` generates its TypeScript client from the resulting OpenAPI schema (`npm run api:types`, comments stripped). Requests that touch a source host carry `credentials {kind, token, username, base_url, owner, author_name, author_email}`; identity alone is valid for a local commit.

## Trust

Every route but `/api/version`, `/docs` and `/openapi.json` requires `Authorization: Bearer <AP_API_TOKEN>`, the shared secret between the web app and the API, checked in constant time. Without a token the API refuses to start — `AP_ALLOW_UNAUTHENTICATED=1` opts into an open API for local development only. Behind that secret, `/api/auth/*` identifies the person through a session or a token it issued; the rules in `action_platform/core/access.py` decide roles, scopes and grants. Which project or app a call may touch is still enforced in the web app's `/api/v1` proxy ([access control](concept_access_control.md)); the CLI and MCP go through that proxy, and its `/api/auth/device/*` forwards to the API for `action-platform login`.

## Workspaces

`AP_HOME` (default `~/.action-platform`, `/data/action-platform` in the image) holds `apps.json` — the registry: id, name, url, path, default branch — and `workspaces/<id>`, one clone per app. Every call that opens a workspace brings `platform.toml` back when it is missing, so an app never errors for something the platform can fix itself.

## Errors

`ActionPlatformError` and its subclasses (`ReleaseError`, `BranchError`, `PullRequestError`, `SyncError`, `TemplateError`, `InstallError`) answer `400 {"detail": "…"}` with a message meant for the user; `HTTPException` carries `404`, `409`, `410` and `422` (`{"code": "needs_install"}` when a repository has no `platform.toml`). Anything else is a `500` and reaches Sentry when `AP_SENTRY_DSN` is set ([observability](concept_observability.md)).
