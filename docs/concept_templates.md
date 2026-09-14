# Templates

```
action-platform init --list
```

| Type | Stacks | Ready with |
|------|--------|-----------|
| `web` | python (FastAPI, FastMCP), go (Gin), node (Fastify, React), java (Spring), kotlin (Spring), ruby (Sinatra) | `/ping`, versioned API, tests, lint, CI |
| `library` | python, go, php, node, java, rust | packaging, version test, publish workflow |
| `docs` | mkdocs | Material theme, strict build in CI |
| `plugin` | chrome | Manifest V3, popup, background, tests, store zip |
| `empty` | — | `platform.toml` + code quality only |

| Cloud | Adds |
|-------|------|
| `aws/lambda` | SAM template, HTTP API, custom domain, deploy workflow, IAM policy |
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

## Adding one

1. In the templates repository, add `projects/<type>/<stack>/<name>/` with a `cookiecutter.json` (`project_name`, `project_slug`, `description`, `package_name`, `github_owner`, `ci`) and a `{{cookiecutter.project_slug}}/` tree.
2. Register it in `index.json`.
3. `ACTION_PLATFORM_TEMPLATES=/path/to/checkout action-platform init <type> <stack> <name> --no-push` to try it.

Nothing to redeploy: the CLI and the API read the repository at `main`.
