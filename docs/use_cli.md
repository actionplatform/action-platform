# CLI

```bash
pipx install action-platform          # library + CLI
pip install "action-platform[mcp]"    # + MCP server
pip install ./apps/api    # + the JSON API the web app uses
```

## Scaffold

```bash
action-platform init                              # interactive: type → stack → template → name → ci
action-platform init web go gin --ci gitlab       # direct
action-platform init web python --cloud docker    # project + deploy overlay
action-platform init ... --no-push                # keep it local
action-platform init --list                       # the templates matrix
action-platform init --source URL[@ref] ...       # templates from another repository (also cloud set, service add)
action-platform install [--type web] [--language python|none] [--ci github|gitlab|jenkins|bitbucket|none] [--dry-run]
                                                  # existing repo: platform.toml, LAST_VERSION (newest vX.Y.Z tag or 0.0.0),
                                                  # AGENTS.md, .code_quality/, CI files (none with --ci none), hooks — never overwrites; --dry-run plans only
action-platform plugin install aws-lambda         # deploy target + overlay for aws/lambda (see use_plugins.md)
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

See [git-flow](concept_git_flow.md).

## Release and operate

```bash
action-platform release [patch|minor|major|X.Y.Z] [--dry-run] [--rc|--stable] [--component web]
action-platform deploy [--version X.Y.Z] [--target name] [--stage dev|prod] [--dry-run]
action-platform rollback [--target name] [--to X.Y.Z] [--stage …]
action-platform diagnose [--target name]
action-platform destroy [--target name]
action-platform deployments [--app id|name] [--sync]      # on the hosted platform: every target, what arrived at each
action-platform deploy-record <target> <version> [--stage s] [--url u] [--failed]
```

`release` plans first (refuses a dirty tree, an existing version or tag), then bumps `LAST_VERSION`, prepends `CHANGELOG.md`, syncs `pyproject.toml` / `package.json` / `Cargo.toml` / `composer.json` / `pom.xml`, `__version__` and version constants, commits `chore(release): X.Y.Z`, tags, pushes, publishes the release on the source host and triggers CI runners. A push the remote refuses undoes the commit and the tag. Off `main`/`master` the version is `X.Y.Z-rc.N`. `--component <name>` releases one [component](concept_releases.md).

`deploy` ships a release, never a working tree: `--version X.Y.Z` names the tag `vX.Y.Z` (or pass the tag itself); without it, HEAD must sit on a release tag, otherwise the command refuses. The tag is checked out for the duration and the branch put back afterwards. It runs the `[deploy]` target's `preflight`, then `create` / `deploy` / `switch_traffic`; `--dry-run` stops after preflight.

## Platform services

```bash
action-platform-api serve [--reload] [--host] [--port] [--cors]   # JSON API for the web app (:7788, OpenAPI at /docs)
action-platform mcp [--http] [--remote]                     # MCP server (local tools, or the hosted platform's)
action-platform login <url> [--scope read,write] [--name label] [--no-browser]   # device flow → bearer token; asks for everything your role allows unless --scope narrows it
action-platform whoami                                      # server — account — scope — on Org / project / app
action-platform logout
action-platform-api db status | migrate [--url …]            # the API's database: revision, migrate on demand
action-platform-api worker [--once] [--interval 2] [--name]  # run queued jobs against AP_DATABASE_URL
```

Credentials from `login` live in `~/.action-platform/credentials.json` (mode 600); `AP_SERVER` + `AP_TOKEN` override them.

## Environment

| Variable | Used by |
|---|---|
| `ACTION_PLATFORM_GITHUB_TOKEN` / `GH_TOKEN` | GitHub without the `gh` CLI |
| `ACTION_PLATFORM_GITLAB_TOKEN` / `GITLAB_TOKEN` | GitLab |
| `ACTION_PLATFORM_BITBUCKET_TOKEN`, `ACTION_PLATFORM_BITBUCKET_USERNAME` | Bitbucket |
| `ACTION_PLATFORM_TEMPLATES`, `ACTION_PLATFORM_TEMPLATES_REPO` | local checkout / repository of the templates matrix |
| `AP_HOME` | where the API keeps its workspaces and the CLI its credentials (default `~/.action-platform`) |
| `AP_SERVER`, `AP_TOKEN` | use this platform and token instead of the credentials file |
| `AP_GIT_AUTHOR_NAME`, `AP_GIT_AUTHOR_EMAIL` | identity for commits when the request carries none (default `Action Platform <cloud@actionplatform.io>`) |
| `AP_SENTRY_DSN` | error reporting, see [observability](concept_observability.md) |

## Tokens and scopes

`action-platform login <server> [--scope …] [--name label]` runs the device flow. Without `--scope` it asks for every scope and every organization; the browser page shows that selection already made, cut to what your role allows, and you can narrow it before approving. `--scope read,write` narrows from the command line instead. In the browser you pick what the token may do — `read` (always), `write` (configuration, branches, pull requests, commits, sync), `release`, `admin` (projects, members, hosts, settings) — and where it may act — one organization or all of them, optionally one project, optionally one app inside it — and the CLI swaps the approved session for a bearer JWT with that scope and reach, valid 90 days, kept in `~/.action-platform/credentials.json`. Scope narrows your role; it never widens it, and the browser only offers what your role can grant. `action-platform whoami` prints server, account, scope and reach; tokens are listed and revoked under **Connected apps** (key icon next to your name in the web app), together with the programs that used them. `AP_SERVER` / `AP_TOKEN` (and `AP_SCOPE` for display) override the file.

## Error reporting

Optional: `pip install "action-platform[sentry]"` and export `AP_SENTRY_DSN` to send CLI crashes to Sentry. Off by default — see [observability](concept_observability.md).
