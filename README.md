<p align="center">
  <img src="https://raw.githubusercontent.com/actionplatform/action-platform/master/docs/assets/cover.png" alt="Action Platform" width="100%">
</p>

<p align="center">
  <strong>Your platform team, as a CLI.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/action-platform/"><img alt="PyPI" src="https://img.shields.io/pypi/v/action-platform?color=2ea44f"></a>
  <a href="https://pypi.org/project/action-platform/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/action-platform"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-blue"></a>
  <a href="https://github.com/actionplatform/templates"><img alt="Templates" src="https://img.shields.io/badge/templates-13%20projects%20%C2%B7%203%20clouds-6f42c1"></a>
</p>

---

Every new service costs the same week: scaffold, lint config, CI, versioning, deploy pipeline, IAM. Then the next one drifts from the last. **Action Platform** turns that week into one command and keeps every project on the same rails — without a control plane to host, a UI to learn, or a vendor to trust with your cloud.

```bash
pipx install action-platform

action-platform init web python fastapi --name "orders" --cloud aws/lambda
```

Thirty seconds later you have a FastAPI service with tests, lint, CI wired, a SAM template, a least-privilege IAM policy, and a GitHub repo already pushed (`--no-push` to keep it local).

## Why teams pick it

| | |
|---|---|
| **One command, whole lifecycle** | `init` → `release` → `deploy` → `rollback` → `diagnose` → `destroy`. Same verbs for a Python API on Lambda, a Go service in Docker, a React app on Amplify. |
| **Templates from production, not tutorials** | Every project template is extracted from a real shipping product. Real layout, real CI, real gotchas already fixed. |
| **Cloud is a layer, not a fork** | Projects stay cloud-agnostic. `--cloud aws/lambda` overlays deploy files; swap to `docker` tomorrow with one command. |
| **Your CI, your account, your git** | Runs on GitHub Actions, GitLab CI or Jenkins you already have. Infra lands in **your** AWS account through OIDC — no long-lived keys, no agent, no SaaS in the loop. |
| **Governance that ships with the code** | Git-flow and Conventional Commits enforced by git hooks before a commit exists and by CI on every PR; changelog generated; `AGENTS.md` for humans and AI agents; Trivy scans; least-privilege IAM in `requirements/`. |
| **Fix once, everywhere** | CI logic lives in versioned shared repos (`ci-scripts`, `ci-github`, `ci-gitlab`, `ci-jenkins`). Bump `v1`, every project picks it up. |

## What you get

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

## Commands

```bash
action-platform init                              # interactive: type → stack → template → name → ci
action-platform init web go gin --ci gitlab       # direct
action-platform init web python --cloud docker    # project + deploy overlay
action-platform init ... --no-push                # skip creating the remote repo
action-platform install [--dry-run]               # existing repo: platform.toml, hooks, code quality, CI — never overwrites

action-platform cloud set aws/lambda              # add or switch the deploy target
action-platform service add postgres --provider aws-rds

action-platform branch feature 42 login           # develop (or main) → pull → feature/42-login → push
action-platform branch hotfix PROJ-7              # from main/master
action-platform gitflow                           # audit current branch + commits; --install-hooks
action-platform pr [--draft] [--dry-run]          # PR for the current branch: target from git-flow, body from commits
action-platform release patch                     # bump, changelog, tag, GitHub release
action-platform deploy --stage prod
action-platform rollback
action-platform diagnose
action-platform destroy
```

Everything a project needs is declared in one file:

```toml
[project]
name = "orders"
type = "web"
stack = "python"
template = "fastapi"
ci = "github"
language = "python"

[source_host]
kind = "github"
repo = "acme/orders"

[deploy]
target = "aws/lambda"

[services]
postgres = "aws-rds"
```

## Use it from an AI client

The platform ships as an MCP server. Claude Code, Codex, Cursor — anything that speaks MCP — gets `list_matrix`, `init_project`, `cloud_set`, `service_add`, `release`, `deploy`, `diagnose` as tools, plus skills that make the agent preview and ask before pushing or deploying.

```bash
pip install "action-platform[mcp]"
action-platform mcp                 # stdio
action-platform mcp --http          # http://127.0.0.1:8765/mcp
```

Claude Code:

```bash
/plugin marketplace add actionplatform/action-platform
/plugin install action-platform@action-platform
```

Any client — add to `.mcp.json`:

```json
{ "mcpServers": { "action-platform": { "command": "uvx", "args": ["--from", "action-platform[mcp]", "action-platform-mcp"] } } }
```

## Extend it

Deploy targets are plugins. Implement the `DeployTarget` contract — `preflight`, `create`, `deploy`, `switch_traffic`, `rollback`, `diagnose`, `delete` — publish it under the `action_platform.deploy_target` entry-point group, and `action-platform deploy` finds it by name.

```python
from action_platform import ActionPlatform, Config
from action_platform.providers import SourceGithub

tool = ActionPlatform(config=Config(source_host=SourceGithub(repo="acme/orders")))
tool.release("minor")
```

Templates are plain cookiecutters in [actionplatform/templates](https://github.com/actionplatform/templates). Add a stack or a cloud with a pull request — the CLI reads `index.toml`, nothing to redeploy. Point `ACTION_PLATFORM_TEMPLATES` at a local checkout while you work on them.

## Ecosystem

| Repo | Role |
|------|------|
| [templates](https://github.com/actionplatform/templates) | projects, clouds, services |
| [ci-scripts](https://github.com/actionplatform/ci-scripts) | the one implementation of setup / check / release / commit lint |
| [ci-github](https://github.com/actionplatform/ci-github) · [ci-gitlab](https://github.com/actionplatform/ci-gitlab) · [ci-jenkins](https://github.com/actionplatform/ci-jenkins) | thin wrappers per CI |
| [strategy](https://github.com/actionplatform/strategy) | why it is built this way |

## License

Apache 2.0.
