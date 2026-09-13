# Architecture

```mermaid
flowchart TB
    browser[Browser]
    agent[Claude Code · Codex · Cursor]
    term[Terminal]

    subgraph web["apps/web — Next.js"]
        ui[Pages + server actions]
        auth[better-auth · drizzle]
        v1["/api/v1/* (bearer proxy)"]
    end

    subgraph api["action-platform api — FastAPI"]
        reg[apps registry]
        ws[(workspaces: one clone per app)]
    end

    core[[action_platform.core]]
    hosts{{GitHub · GitLab · Bitbucket · generic}}

    browser --> ui
    ui --> auth
    ui -->|"JSON + credentials per request"| api
    agent -->|"mcp --remote · Bearer token"| v1
    v1 --> api
    term -->|"action-platform …"| core
    api --> core
    api --> ws
    core -->|"push · release · pull request"| hosts
```

## Packages

```
action_platform/
  core/
    manifest/     platform.toml: read_platform, write_source_host, write_deploy_target, write_service
    scaffold/     templates (matrix from index.toml), generate (cookiecutter, cloud/service overlays, push), install
    flow/         git (subprocess wrapper), gitflow (rules), branching, pullrequest
    release/      versioning, changelog, components, release, deploy (rollback, diagnose, destroy)
    config.py     Config.from_toml → source host, deploy targets, components
    context.py    Context, DeployResult, Diagnosis, PRRef, ReleaseRef
    action_platform.py   the facade the CLI, MCP and API call
  providers/
    source/       rest (urllib helper), github, gitlab, bitbucket, generic; build_source_host(kind, …)
  abc/            SourceHost, CIRunner, DeployTarget contracts
  api/            FastAPI: registry (apps.json + workspaces), models (the OpenAPI contract), server, credentials
  remote/         client (urllib) + device-flow login + credentials file
  mcp/            server (local or --remote), tools/*, prompts
  cli/            Typer commands
  observability.py   Sentry init shared by the CLI and the API (docs/observability.md)
  hooks/          commit-msg, pre-commit, pre-push, gitflow.sh
apps/web/         the web app
deploy/           Dockerfiles, compose, install.sh
```

Deploy targets and CI runners are plugins discovered through the `action_platform.deploy_target` / `action_platform.ci_runner` entry-point groups (`core/module.py`).

## The API

`action-platform api` — one process, file-backed, single-tenant. Multi-tenancy (organizations, projects, who may touch which app) is the web app's job; the API trusts its caller.

| Endpoint | |
|---|---|
| `GET /api/matrix`, `GET /api/gitflow/rules`, `GET /api/version` | static |
| `GET/POST /api/apps`, `POST /api/apps/init`, `DELETE /api/apps/{id}` | registry: add by git url (clone), generate from a template, remove (deletes the clone) |
| `POST /api/apps/{id}/sync`, `/push` | fetch + fast-forward; create the remote and push |
| `GET /api/apps/{id}`, `/gitflow`, `/commits`, `/branches`, `/tags` | state of the clone |
| `POST /api/apps/{id}/release`, `/deploy`, `GET /diagnose` | actions; `dry_run` defaults to true |

Every response is a Pydantic model in `api/models.py`; `apps/web` generates its TypeScript client from the resulting OpenAPI schema (`npm run api:types`).

## How credentials travel

```mermaid
sequenceDiagram
    participant M as Member (browser)
    participant W as apps/web
    participant DB as web database
    participant A as action-platform api
    participant G as Code host

    M->>W: Connect with GitHub
    W->>G: OAuth authorize → code
    G-->>W: access (+ refresh) token
    W->>DB: source_host (token AES-256-GCM)

    M->>W: Push / Release
    W->>DB: read token (refresh if expiring)
    W->>A: POST /api/apps/{id}/release {credentials}
    A->>A: config.source_host = build_source_host(kind, token)
    A->>A: git_auth(): credential helper via GIT_CONFIG_*
    A->>G: git push · REST create release
    A-->>W: result
    Note over A: nothing stored
```

1. A member connects a code host in the web app (OAuth) or pastes a token. The token is AES-256-GCM encrypted (`lib/crypto.ts`, key derived from `BETTER_AUTH_SECRET`) and stored in `source_host`.
2. An app remembers which host it uses (`app.source_host_id`).
3. A push / release server action decrypts the token — refreshing it first for GitLab / Bitbucket — and sends it in the request body as `credentials {kind, token, username, base_url, owner}`.
4. The API rebuilds `config.source_host` with that token (`api/core/credentials.py: apply`) and wraps the git calls in `git_auth()`. The credentials go into a `contextvars.ContextVar` that `core/flow/git.git_env()` reads when it spawns git, so they belong to that request only — concurrent requests on other threads never see them and the process environment is never touched. Git receives them as a credential helper through `GIT_CONFIG_COUNT/KEY/VALUE`, so the token never lands in `.git/config` or on a command line, and the host's own helpers (keychain, `gh`) are cleared for that call.
5. Nothing is stored on the API side.

## The web app's data

```mermaid
erDiagram
    user ||--o{ member : "belongs to"
    user ||--o{ session : has
    user ||--o{ account : "signs in with"
    organization ||--o{ member : has
    organization ||--o{ invitation : sends
    organization ||--o{ project : owns
    organization ||--o{ source_host : "connects"
    project ||--o{ app : groups
    source_host o|--o{ app : "pushes with"
    app {
        string registry_id "id on the Python API"
        string source_host_id
    }
    source_host {
        string kind "github | gitlab | bitbucket | generic"
        string auth_kind "oauth | token"
        string token_encrypted
        string refresh_token_encrypted
        datetime expires_at
    }
    session {
        string active_organization_id
    }
```

`user`, `session`, `account`, `verification`, `device_code` come from better-auth (and its `organization` / `deviceAuthorization` plugins); `project`, `app`, `source_host` are the platform's. Same schema in three dialects under `apps/web/lib/db/schema/`, migrations per dialect under `apps/web/drizzle/`, applied on boot.

## Trust between web and API

The browser never talks to the Python API. The web app authenticates users (sessions, roles) and calls the API server-side over the private network; the CLI and MCP go through the web app's `/api/v1` proxy with a bearer token from `action-platform login`. Between web and API a shared secret, `AP_API_TOKEN`, is sent as `Authorization: Bearer` and checked in constant time on every route but `/api/version`, so only the web app can drive clones, git and the workspaces.
