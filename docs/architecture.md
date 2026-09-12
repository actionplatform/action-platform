# Architecture

```
                 browser                 Claude Code / Codex / Cursor          terminal
                    │                              │                              │
              apps/web (Next.js)          action-platform mcp --remote     action-platform …
              better-auth · drizzle                │  bearer token                │
                    │  server actions              │                              │
                    ├───────── /api/v1/* ◄─────────┘                              │
                    ▼                                                             ▼
          action-platform api (FastAPI)  ◄──── same core ────►  action_platform.core (in-process)
                    │
          ~/.action-platform/workspaces/<id>   one clone per app
                    │
          providers/source: GitHub · GitLab · Bitbucket · generic
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

1. A member connects a code host in the web app (OAuth) or pastes a token. The token is AES-256-GCM encrypted (`lib/crypto.ts`, key derived from `BETTER_AUTH_SECRET`) and stored in `source_host`.
2. An app remembers which host it uses (`app.source_host_id`).
3. A push / release server action decrypts the token — refreshing it first for GitLab / Bitbucket — and sends it in the request body as `credentials {kind, token, username, base_url, owner}`.
4. The API rebuilds `config.source_host` with that token (`api/credentials.py: apply`) and wraps the git calls in `git_auth()`, which injects a credential helper through `GIT_CONFIG_COUNT/KEY/VALUE` so git authenticates without the token touching `.git/config` or a command line. The host's own helpers (keychain, `gh`) are cleared for that call.
5. Nothing is stored on the API side.

## The web app's data

`organization`, `member`, `invitation` (better-auth), `user`, `session`, `account`, `verification`, `device_code` (device flow), `project`, `app`, `source_host`. Same schema in three dialects under `apps/web/lib/db/schema/`, migrations per dialect under `apps/web/drizzle/`, applied on boot.
