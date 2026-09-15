# Architecture

```mermaid
flowchart TB
    browser[Browser]
    agent[Claude Code · Codex · Cursor]
    term[Terminal]

    subgraph web["apps/web — Next.js"]
        ui[Pages + server actions]
        auth[sessions · cookies via /api/auth]
        v1["/api/v1/* → rewrite to the API"]
    end

    subgraph api["action-platform-api serve — FastAPI"]
        reg[apps registry]
        ws[(disposable clones under the temp dir)]
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
    manifest/     Manifest: platform.toml as an object (project, source_host, services; set_source_host, set_deploy_target, set_service)
    scaffold/     store (TemplateSource, TemplateStore: checkouts), templates (Matrix, Leaf, Cloud, Service), detect (LanguageDetector), install (Installer: plan/apply), generate (cookiecutter, overlays, push)
    flow/         repository (Repository: every git command on one clone, follow_remote, stashed), workflow (GitFlow: audit, start, propose, open_pr, install_hooks), gitflow (the rules as pure functions), git (ref/url policy, per-request credentials)
    release/      versioning (Version, VersionFiles), changelog, components, release (Releaser: plan → apply), deploy (Deployer)
    config.py     Config.from_toml → source host, deploy targets, components
    context.py    Context, DeployResult, Diagnosis, PRRef, ReleaseRef
    action_platform.py   ActionPlatform: the facade the CLI, MCP and API call (releaser, deployer, flow)
  providers/
    source/       rest (urllib helper), github, gitlab, bitbucket, generic; build_source_host(kind, …)
  abc/            SourceHost, CIRunner, DeployTarget, WorkingCopy, TemplateStore contracts
  remote/         client (urllib): device-flow login, scoped token exchange, every /api/v1 call; credentials file
  mcp/            server (local or --remote), tools/{matrix,project,flow,lifecycle,remote}, prompts, annotations
  cli/            Typer commands: init install branch gitflow pr release deploy rollback diagnose destroy cloud service mcp login logout whoami
  observability.py   Sentry init shared by the CLI and the API (docs/concept_observability.md)
  hooks/          commit-msg, pre-commit, pre-push, gitflow.sh
apps/web/         the web app
deploy/           Dockerfiles, compose, install.sh
apps/api/app/  (package `app`, depends on the library, never the other way round)
  api/            FastAPI: app (factory, AP_API_TOKEN middleware, Sentry), gate (the /api/v1 gate: role ∩ scope ∩ reach), deps, ratelimit, routers (workspace, directory, management, imports, auth)
  core/           abc (HostProvider, HostDirectory, ImportSource: one implementation per code host), access (Caller, rules, enrich), auth (AuthService, crypto, jwt, passwords, secrets, cookies), db (models, database, migrations), cli (serve, worker, db), shared (clock, ids, urls, http, credentials, git_auth)
  repositories/   registry (`registry` table), drafts (`draft` table: pending edits), source (the registry this process opens)
  services/       directory (organizations, projects, teams, invitations, hosts, oauth_apps, template_sources), apps (inventory, scaffolding, remote), workspace (disposable clones, manifest, configuration, flow, state, lifecycle), hosts (one HostProvider per code host, OAuth state, access report), activity (releases and pull requests, one ImportSource per host), organization_import (preview and the import steps), catalog (matrix view, published index), jobs (queue)
  schemas/        the Pydantic models behind the OpenAPI contract
  worker.py       `action-platform-api worker`: runs queued jobs with the same services

```

### Objects in the core

Every operation starts from a `Repository` — one clone, every git command as a method, credentials and identity taken from the request context — and layers on top of it:

| Object | Does | Where used |
|---|---|---|
| `Manifest.of(root)` | reads and edits `platform.toml` table by table | install, generate, API configuration |
| `GitFlow(repo)` | `audit()`, `start(kind, code)`, `propose()`, `open_pr()`, `install_hooks()` | CLI `branch`/`pr`/`gitflow`, MCP, API flow |
| `Releaser(config, repo)` | `plan(level)` → `ReleasePlan` (dry run), `apply(plan)`; a refused push undoes commit and tag | CLI/MCP/API release |
| `Deployer(config, repo)` | deploy, rollback, diagnose, destroy through the `[deploy]` targets | CLI/MCP/API deploy |
| `Installer(root, …)` | `plan()` / `apply()`: platform.toml, LAST_VERSION, AGENTS.md, quality config, CI files, hooks | CLI `install`, API import |
| `TemplateStore()` | `official()` and `checkout(source)` clones of template repositories | matrix loading |
| `Version` / `VersionFiles` | semver value object; the files a project declares its version in | releaser |

Rules that need no repository — branch names, commit messages, merge targets — stay pure functions in `flow/gitflow.py`, shared with `ci-scripts/gitflow.sh`. `ActionPlatform` is the facade the CLI, MCP and API call; it exposes `releaser`, `deployer` and `flow` for one project.

Deploy targets and CI runners are plugins discovered through the `action_platform.deploy_target` / `action_platform.ci_runner` entry-point groups (`core/module.py`).

## The API

One process, file-backed, single-tenant; every route, the credentials contract and the OpenAPI client are in [api](use_api.md).

## How credentials travel

```mermaid
sequenceDiagram
    participant M as Member (browser)
    participant W as apps/web
    participant DB as web database
    participant A as action-platform-api serve
    participant G as Code host

    M->>W: Connect with GitHub
    W->>G: OAuth authorize → code
    G-->>W: access (+ refresh) token
    W->>DB: source_host (token AES-256-GCM)

    M->>W: Push / Release / Commit
    W->>DB: read token (refresh if expiring) + organization commit identity
    W->>A: POST /api/apps/{id}/release {credentials + author}
    A->>A: config.source_host = build_source_host(kind, token)
    A->>A: git_auth(): credential helper + GIT_AUTHOR_* via GIT_CONFIG_* / env
    A->>G: git push · REST create release
    A-->>W: result
    Note over A: nothing stored
```

1. A member connects a source host (OAuth through `/api/v1/oauth/…`) or pastes a token (`POST /api/v1/hosts`). The API seals it with AES-256-GCM (`api/auth/crypto.py`, key derived from the auth secret through HKDF) and stores it in `source_host`.
2. An app remembers which host it uses (`app.source_host_id`).
3. On a push / release through `/api/v1`, the gate opens the token — refreshing it first through the OAuth app when it expired — and adds it to the request as `credentials {kind, token, username, base_url, owner, author_name, author_email}` before the call reaches the workspace route. The web app never sees a token.
4. The API rebuilds `config.source_host` with that token (`api/core/credentials.py: apply`) and wraps the git calls in `git_auth()`. The credentials go into a `contextvars.ContextVar` that `core/flow/git.git_env()` reads when it spawns git, so they belong to that request only — concurrent requests on other threads never see them and the process environment is never touched. Git receives them as a credential helper through `GIT_CONFIG_COUNT/KEY/VALUE`, so the token never lands in `.git/config` or on a command line, and the host's own helpers (keychain, `gh`) are cleared for that call.
5. Nothing about the call is stored beyond the imported releases and pull requests.

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
    organization ||--o{ team : has
    organization ||--o{ template_source : adds
    organization ||--o| organization_setting : "commit identity"
    team ||--o{ team_member : has
    team o|--o{ project : owns
    project ||--o{ app : groups
    source_host o|--o{ app : "pushes with"
    app ||--o{ release : "imported"
    app ||--o{ pull_request : "imported"
    user ||--o{ api_token : "mints"
    api_token ||--o{ api_token_client : "used by"
    app {
        string registry_id "id on the Python API"
        string source_host_id
        datetime last_synced_at
    }
    api_token {
        string organization_id "null = every organization"
        string scope "read write release admin"
        string project_id
        string app_id
        datetime expires_at
        datetime revoked_at
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

`user`, `session`, `account`, `verification`, `device_code`, `organization`, `member`, `invitation` were created by better-auth and are now written by the API's `AuthService` (`apps/api/app/core/auth/`), with the same password hashes and cookie signatures so nothing had to be re-issued; `team`, `team_member`, `project`, `app`, `source_host`, `release`, `pull_request`, `template_source`, `organization_setting`, `api_token`, `api_token_client` are the platform's. Same schema in three dialects under `apps/web/lib/db/schema/`, migrations per dialect under `apps/web/drizzle/` (0001–0014), applied on boot. The Python API mirrors the same tables in `apps/api/app/core/db/models.py` and, given `AP_DATABASE_URL`, connects to the same database, adopts it and adds its own tables (`job`) through Alembic — see [database](concept_database.md).

## Trust between web and API

The web app holds the session cookie the API signed, asks `GET /api/auth/session` who the caller is, and calls the API's internal routes (`/api/apps/…`) server-side over the private network with the shared secret `AP_API_TOKEN` (`Authorization: Bearer`, constant-time check on every route but `/api/version`). The CLI, MCP and the browser reach the user-facing prefixes — `/api/v1/*` and `/api/auth/*` — through the platform's public address: the web app rewrites those paths to the API unchanged, and the API's gate identifies the caller (a JWT from `action-platform login` carrying user, organization, scope and reach, checked against its `api_token` row; or a session), then applies role ∩ scope ∩ reach before the call reaches a workspace ([API](use_api.md)).
