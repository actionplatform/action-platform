# Templates

```
action-platform init --list
```

| Type | Stacks | Ready with |
|------|--------|-----------|
| `web` | python (FastAPI, FastMCP, remote MCP with OAuth bearer auth), go (Gin), node (Fastify, React), java (Spring), kotlin (Spring), ruby (Sinatra) | `/health` (never `/ping` — API Gateway keeps that path on `execute-api`), versioned API, tests, lint, CI |
| `library` | python, go, php, node, java, rust | packaging, version test, publish workflow |
| `automation` | python (basic, scheduled) | `python -m app` entrypoints, tests per task |
| `job` | python | runs once and exits with a status code, logs to stdout, config from env, tests; cron, Dokploy and Jenkinsfile schedule examples |
| `docs` | mkdocs, markdown | mkdocs: Material theme, strict build in CI; markdown: plain pages, `AGENTS.md`/`CLAUDE.md`, an example agent skill, link and format checks in CI, no build |
| `plugin` | chrome | Manifest V3, popup, background, tests, store zip |
| `empty` | — | `platform.toml` + code quality only |

| Cloud | Adds |
|-------|------|
| `aws/lambda` | SAM template, HTTP API, custom domain, deploy workflow, IAM policy — for every `web` language: Mangum for Python, the Lambda Web Adapter for Node and Spring (Java, Kotlin), `aws-lambda-go-api-proxy` for Go, a Rack call for Ruby; the plugin `apx-aws-lambda` carries the canonical copy |
| `aws/amplify` | `amplify.yml`, security headers, start-job workflow, IAM policy |
| `docker` | Dockerfile per language, compose |

| Service | Providers |
|---------|-----------|
| `postgres` | docker (local), aws-rds (Terraform/OpenTofu + SSM) |

## Where they come from

[actionplatform/templates](https://github.com/actionplatform/templates): plain cookiecutters indexed by `index.json`.

```toml
[projects.web.python.fastapi]
default = true
description = "FastAPI + uvicorn + pydantic"

[cloud.aws.lambda]
description = "SAM, HTTP API, custom domain"
types = ["web"]
languages = ["python", "go", "node"]

[service.postgres]
description = "PostgreSQL"
providers = ["docker", "aws-rds"]
```

`action-platform init` clones (and caches) the repository, reads the index, renders `projects/<type>/<stack>/<template>` with cookiecutter and, with `--cloud`, overlays `cloud/<provider>/<service>` on top. The web app's **Templates** catalog and **Create project** wizard read the same index through the API's `/api/matrix`.

Every template ships `platform.toml`, `.code_quality/`, `AGENTS.md`, tests and a CI file for the chosen provider that calls the shared [ci-scripts](https://github.com/actionplatform/ci-scripts).

## Other repositories

The official catalog always comes from [actionplatform/templates](https://github.com/actionplatform/templates) at `main`. The API does not wait for its clone to refresh: it fetches `index.json` raw from the repository (`ACTION_PLATFORM_TEMPLATES_INDEX`; `ACTION_PLATFORM_TEMPLATES_REF` picks the branch) and revalidates it every minute with the ETag (`ACTION_PLATFORM_TEMPLATES_INDEX_TTL`, seconds) — a 304 costs nothing and answers the catalog from it — labels, frameworks and icons included — so a merged template shows in the web app without a redeploy; the clone is still what `init` copies from. When the fetch fails the clone's `index.json` answers. Next to it an organization can add **any git repository**:

- a plain repository (a starter, a reference service) becomes **one template**: a new app starts as a copy of that tree at the chosen branch or tag; the platform detects the language (`pyproject.toml`, `go.mod`, `package.json`…), keeps an existing `platform.toml` (renaming the project) or adds `platform.toml`, `.code_quality/`, CI files and hooks the same way `action-platform install` does;
- a repository with an `index.json` at the root is read as a **catalog** with the official layout (`projects/`, `cloud/`, `service/`).

| Where | How |
|---|---|
| Web app | Templates → **Template repositories** → *Add repository* (name, git URL, branch or tag). Owners and admins only. Private repositories are cloned with the organization's connected source host. Every template, cloud and service then shows its source; the wizard, Configuration and the cloud overlays use the right repository automatically. |
| CLI | `action-platform init --source https://github.com/acme/templates.git@main` (also `cloud set --source`, `service add --source`). |
| MCP (local) | `list_matrix(source="url[@ref]")`, then the same `source` on `init_project`, `cloud_set`, `service_add`. |
| MCP (remote) | `list_matrix` already merges the organization's repositories; pass the source's `name` to `init_app`, `set_cloud`, `add_service`. |

Names are unique per organization and `official` is reserved. A repository that cannot be cloned shows as *Unavailable* with the error, without hiding the others.

### Ownership and retention on the API

A template repository belongs to the organization that added it:

- `/api/v1` reads a `source` — a name, or `{name, url, ref}` — only from the calling organization's own list. A name it does not have, or a `url`/`ref` that differs from the one registered under that name, answers `400 template source <name> not found`, even when another organization added that URL.
- The API keeps each organization's clones in a directory of its own (`~/.cache/action-platform/sources/owners/<hash of the organization id>/<hash of url@ref>`). Two organizations that add the same URL get two clones, each fetched with its own organization's source host.
- Every read (`GET /api/v1/matrix`, `apps/init`, `apps/{id}/cloud`, `apps/{id}/services`) fetches the repository with the organization's current credentials first. When that fetch fails the clone is deleted and the call fails; the copy on disk is never served instead. The CLI and the local MCP keep their own cache and still fall back to it offline.

A clone is kept only while the organization can still read the repository. It is deleted when:

| Event | What goes |
|---|---|
| `DELETE /api/v1/template-sources/{id}` | that source's clone |
| `DELETE /api/v1/hosts/{id}`, `DELETE /api/v1/oauth/{provider}/hosts/{login}` | every clone of the organization; the next read clones again with the credentials left |
| a refresh fails (token revoked, access removed, repository gone) | that source's clone |
| the organization is deleted | every clone of the organization |

## How a template is rendered

Every cookiecutter template, official or not, renders in a separate process, in a temporary directory of its own, with a sandboxed Jinja environment (no access to Python internals from a template or from the values typed in the wizard). That process gets only `PATH` and the locale from the environment, with a `HOME` and `TMPDIR` of its own: no API secret, database URL or source host token reaches it. The result is copied into the project afterwards.

Only the official repository (`ACTION_PLATFORM_TEMPLATES` or its clone) and the overlays of installed plugins run cookiecutter hooks. A template from any other repository renders text only and is refused when it has `hooks/` (`pre_prompt`, `pre_gen_project`, `post_gen_project`), or `_extensions`, `_jinja2_env_vars`, `template` or `templates` in its `cookiecutter.json`. In every template, plain repositories and plain overlays, a symlink must point at a file inside the same template; one that leaves it, or points at a directory, is refused. `{% include %}` reads only files of the template itself.

## Adding one

1. In the templates repository, add `projects/<type>/<stack>/<name>/` with a `cookiecutter.json` (`project_name`, `project_slug`, `description`, `package_name`, `github_owner`, `author`, `license`, `source_host`, `ci` — owner and author empty, licence `none` by default) and a `{{cookiecutter.project_slug}}/` tree.
2. Register it in `index.json`.
3. `ACTION_PLATFORM_TEMPLATES=/path/to/checkout action-platform init <type> <stack> <name> --no-push` to try it.

Nothing to redeploy: the CLI and the API read the repository at `main`.
