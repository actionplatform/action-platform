# CLI

```bash
pipx install action-platform          # library + CLI
pip install "action-platform[mcp]"    # + MCP server
pip install "action-platform[api]"    # + the JSON API the web app uses
```

## Scaffold

```bash
action-platform init                              # interactive: type → stack → template → name → ci
action-platform init web go gin --ci gitlab       # direct
action-platform init web python --cloud docker    # project + deploy overlay
action-platform init ... --no-push                # keep it local
action-platform init --list                       # the templates matrix
action-platform init --source URL[@ref] ...       # templates from another repository (also cloud set, service add)
action-platform install [--dry-run]               # existing repo: platform.toml, hooks, code quality, CI — never overwrites
action-platform cloud set aws/lambda              # add or switch the deploy target
action-platform service add postgres --provider aws-rds
```

`init` renders a cookiecutter from the matrix, applies the cloud overlay, then by default creates the remote repository through `[source_host]` and pushes the first commit.

## Git-flow

```bash
action-platform branch feature 42 login           # develop (or main) → pull → feature/42-login → push
action-platform branch hotfix PROJ-7              # from main/master
action-platform gitflow [--install-hooks]         # audit current branch + commits
action-platform pr [--draft] [--dry-run]          # pull request: target from the rules, body from the commits
```

See [git-flow](git-flow.md).

## Release and operate

```bash
action-platform release [patch|minor|major|X.Y.Z] [--dry-run] [--rc|--stable] [-c web]
action-platform deploy [--stage dev|prod] [--dry-run]
action-platform rollback [--to X.Y.Z]
action-platform diagnose
action-platform destroy
```

`release` bumps `LAST_VERSION`, prepends `CHANGELOG.md`, syncs `pyproject.toml` / `package.json` / `Cargo.toml` / `composer.json` and `__version__`, commits `chore(release): X.Y.Z`, tags, pushes, publishes the release on the source host and triggers CI runners. Off `main`/`master` the version is `X.Y.Z-rc.N`. `-c <name>` releases one [component](releases.md).

`deploy` runs the `[deploy]` target's `preflight`, then `create` / `deploy` / `switch_traffic`; `--dry-run` stops after preflight.

## Platform services

```bash
action-platform api [--reload] [--host] [--port] [--cors]   # JSON API for the web app (:7788, OpenAPI at /docs)
action-platform mcp [--http] [--remote]                     # MCP server
action-platform login <url> [--no-browser]                  # sign in to a hosted platform
action-platform whoami
action-platform logout
```

Credentials from `login` live in `~/.action-platform/credentials.json` (mode 600); `AP_SERVER` + `AP_TOKEN` override them.

## Environment

| Variable | Used by |
|---|---|
| `ACTION_PLATFORM_GITHUB_TOKEN` / `GH_TOKEN` | GitHub without the `gh` CLI |
| `ACTION_PLATFORM_GITLAB_TOKEN` / `GITLAB_TOKEN` | GitLab |
| `ACTION_PLATFORM_BITBUCKET_TOKEN`, `ACTION_PLATFORM_BITBUCKET_USERNAME` | Bitbucket |
| `ACTION_PLATFORM_TEMPLATES`, `ACTION_PLATFORM_TEMPLATES_REPO` | local checkout / repository of the templates matrix |
| `AP_HOME` | where the API keeps `apps.json`, workspaces and credentials (default `~/.action-platform`) |
