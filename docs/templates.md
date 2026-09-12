# Templates

```
action-platform init --list
```

| Type | Stacks | Ready with |
|------|--------|-----------|
| `web` | python (FastAPI, FastMCP), go (Gin), node (React) | `/ping`, versioned API, tests, lint, CI |
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

[actionplatform/templates](https://github.com/actionplatform/templates): plain cookiecutters indexed by `index.toml`.

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

## Adding one

1. In the templates repository, add `projects/<type>/<stack>/<name>/` with a `cookiecutter.json` (`project_name`, `project_slug`, `description`, `package_name`, `github_owner`, `ci`) and a `{{cookiecutter.project_slug}}/` tree.
2. Register it in `index.toml`.
3. `ACTION_PLATFORM_TEMPLATES=/path/to/checkout action-platform init <type> <stack> <name> --no-push` to try it.

Nothing to redeploy: the CLI and the API read the repository at `v1`.
