# API

`action-platform api` — the JSON API the web app drives; a FastAPI process listening on `:7788` with OpenAPI at `/docs`. It is released as its own component (`api/vX.Y.Z`, image `actionplatformio/action-platform-api`) and reports that version in `GET /api/version`.

`action-platform api` — one process, file-backed, single-tenant. Multi-tenancy (organizations, projects, who may touch which app) is the web app's job; the API trusts its caller.

| Endpoint | |
|---|---|
| `GET /api/version` (`{version, api}`), `GET /api/matrix`, `POST /api/matrix {sources}`, `GET /api/gitflow/rules` | static; `POST /matrix` merges extra template repositories |
| `GET /api/apps`, `POST /api/apps {url, name, install}`, `POST /api/apps/init`, `DELETE /api/apps/{id}` | registry: clone a repository (installing the platform when asked), generate from a template, remove the workspace |
| `POST /api/apps/{id}/sync {reset}`, `/push {private}` | fetch + fast-forward (stash around it, follow a rewritten remote, leave a merged branch); create the remote and push |
| `GET /api/apps/{id}`, `/gitflow`, `/commits`, `/branches`, `/tags`, `/releases`, `/changes` | state of the workspace; a clone that lost `platform.toml` gets it back on the spot |
| `GET/PUT /api/apps/{id}/manifest`, `POST /cloud`, `/services`, `/install`, `/discard`, `/commit {message, branch, push, pull_request}` | configuration: edit platform.toml, apply overlays, reinstall, drop or commit the changes (on a new git-flow branch with a pull request when the branch is protected) |
| `POST /api/apps/{id}/branches`, `/checkout`, `GET/POST /pull-request` | git-flow: start a branch, switch, propose and open a pull request |
| `POST /api/apps/{id}/release {level, branch, dry_run}`, `/deploy`, `GET /diagnose` | release (fast-forwarded first; a refused push undoes commit and tag), deploy, diagnose; `dry_run` defaults to true |

Every response is a Pydantic model under `api/schemas/`; `apps/web` generates its TypeScript client from the resulting OpenAPI schema (`npm run api:types`, comments stripped). Requests that touch a source host carry `credentials {kind, token, username, base_url, owner, author_name, author_email}`; identity alone is valid for a local commit.

## Trust

Every route but `/api/version`, `/docs` and `/openapi.json` requires `Authorization: Bearer <AP_API_TOKEN>`, the shared secret between the web app and the API, checked in constant time. The API trusts its caller for everything else — organizations, projects, roles, scopes and reach are the web app's job, enforced in its `/api/v1` proxy ([access control](concept_access_control.md)). The CLI and MCP never talk to this API directly; they go through the proxy.

## Workspaces

`AP_HOME` (default `~/.action-platform`, `/data/action-platform` in the image) holds `apps.json` — the registry: id, name, url, path, default branch — and `workspaces/<id>`, one clone per app. Every call that opens a workspace brings `platform.toml` back when it is missing, so an app never errors for something the platform can fix itself.

## Errors

`ActionPlatformError` and its subclasses (`ReleaseError`, `BranchError`, `PullRequestError`, `SyncError`, `TemplateError`, `InstallError`) answer `400 {"detail": "…"}` with a message meant for the user; `HTTPException` carries `404`, `409`, `410` and `422` (`{"code": "needs_install"}` when a repository has no `platform.toml`). Anything else is a `500` and reaches Sentry when `AP_SENTRY_DSN` is set ([observability](concept_observability.md)).
