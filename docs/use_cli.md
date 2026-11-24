# CLI

```bash
pipx install "action-platform[mcp]"   # library + CLI + MCP server
```

## Scaffold

```bash
action-platform init                              # interactive: type → stack → template → name → ci
action-platform init web go gin --ci gitlab       # direct
action-platform init web python --cloud docker    # project + deploy overlay
action-platform init ... --no-push                # keep it local
action-platform init ... --owner acme --author "Acme Inc" --license mit --host gitlab --public
action-platform init --list                       # the templates matrix
action-platform init --source URL[@ref] ...       # templates from another repository (also cloud set, service add)
action-platform install [--type web] [--language python|none] [--ci github|gitlab|jenkins|bitbucket|none] [--version X.Y.Z] [--dry-run]
                                                  # existing repo: platform.toml, LAST_VERSION (newest release tag, else the manifest version, else the newest CHANGELOG entry, else 0.0.0),
                                                  # AGENTS.md, .code_quality/, CI files (none with --ci none), hooks — never overwrites; --dry-run plans only
action-platform plugin install aws-lambda         # deploy target + overlay for aws/lambda (see use_plugins.md)
action-platform cloud set aws/lambda              # add or switch the deploy target
action-platform service add postgres --provider aws-rds
```

`init` renders a cookiecutter from the matrix, applies the cloud overlay, then by default creates the remote repository through `[source_host]` and pushes the first commit.

Whose project it is comes from you, never from the templates:

| Option | Default |
|---|---|
| `--owner` | the account the host's credentials belong to (`ACTION_PLATFORM_GITHUB_TOKEN`/`GH_TOKEN`, else `gh`; `ACTION_PLATFORM_GITLAB_TOKEN`; `ACTION_PLATFORM_BITBUCKET_USERNAME`), else asked; without a terminal `init` stops and asks for `--owner` or `--no-push` |
| `--author` | `git config user.name`; it goes into the manifest's authors and the LICENSE copyright |
| `--license mit\|apache-2.0\|none` | asked; `none` without a terminal — no `LICENSE` file |
| `--host github\|gitlab\|bitbucket` | `gitlab` or `bitbucket` when `--ci` names it, else `github` |
| `--public` / `--private` | private |

The owner names `[source_host] repo` and, in the templates, the repository URLs, Go module path, npm scope, Composer vendor and Java/Kotlin package (`com.<owner>.<name>`). With no owner (`--no-push`), `platform.toml` has no `[source_host]` and those use `example` until you set one.

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
action-platform scopes                                    # the repository's [[scopes]]: name, kind, criticality; none means it does not deploy
action-platform readiness [--version X.Y.Z] [--target name] [--stage|--scope name]
action-platform deploy [--version X.Y.Z] [--target name] [--stage|--scope name] [--dry-run]   # a dispatched Jenkins target needs the app's connected server: deploy it from the platform
action-platform rollback [X.Y.Z] [--target name] [--stage|--scope name]
action-platform diagnose [--target name]
action-platform destroy [--target name]
action-platform deployments [--app id|name] [--sync]      # on the hosted platform: every target, what arrived at each; --sync asks the observed pipelines first
action-platform logs <job-id> [--follow]                  # on the hosted platform: what the worker wrote for a job, live with -f
action-platform deploy-record <target> <version> [--stage|--scope s] [--url u] [--failed] [--app id|name]   # on the hosted platform: write down a delivery made outside it
```

`release` plans first (refuses a dirty tree, an existing version or tag), then bumps `LAST_VERSION`, prepends `CHANGELOG.md`, syncs `pyproject.toml` / `package.json` / `Cargo.toml` / `composer.json` / `pom.xml`, `__version__` and version constants, commits `chore(release): X.Y.Z`, tags, pushes, publishes the release on the source host and triggers CI runners. A push the remote refuses undoes the commit and the tag. Off `main`/`master` the version is `X.Y.Z-rc.N`. `--component <name>` releases one [component](concept_releases.md).

`readiness` says whether a release can reach a stage without building or changing anything: the static checks (stage, tag shape, manifests at the tag's version, lockfiles) and what the `[deploy]` targets can verify (credentials, permissions, the destination's state); one line per check with its fix, a verdict per stage, exit `1` when something blocks. The same checks the hosted platform runs after every release — see [deployments › readiness](concept_deployments.md#readiness).

`deploy` ships a release, never a working tree: `--version X.Y.Z` names the tag `vX.Y.Z` (or pass the tag itself); without it, HEAD must sit on a release tag, otherwise the command refuses. The tag is checked out for the duration and the branch put back afterwards. It runs the `[deploy]` target's `preflight`, then `create` / `deploy` / `switch_traffic`; `--dry-run` stops after preflight.

## Platform services

```bash
action-platform-api serve [--reload] [--host] [--port] [--cors]   # JSON API for the web app (:7788, OpenAPI at /docs)
action-platform mcp [--http] [--remote]                     # MCP server (local tools, or the hosted platform's)
action-platform login <url> [--scope read,write] [--name label] [--no-browser]   # device flow → bearer token; asks for everything your role allows unless --scope narrows it
action-platform login <url> --token < token.txt               # no browser: keep a token created in the web app or by `action-platform-api tokens issue` (stdin or AP_TOKEN)
action-platform whoami                                      # server — account — scope — on Org / project / app
action-platform logout
action-platform access audit | who | grant | revoke | offboard | sync   # service access on the logged-in platform; dry runs unless --apply
action-platform-api db status | migrate [--url …]            # the API's database: revision, migrate on demand
action-platform-api db backup [--out FILE|-] | restore FILE|- [--force]   # pg_dump / psql; restore refuses a database with tables unless --force
action-platform-api worker [--once] [--interval 2] [--name]  # run queued jobs against AP_DATABASE_URL
action-platform-api users list | create | reset-password | disable | enable   # accounts, from inside the API container
action-platform-api tokens issue EMAIL [--scope …] [--org …]  # a bearer token for automation on stdout
action-platform-api setup token                              # the token the first sign-up needs, until an account exists
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

Without a browser, `action-platform login <server> --token` keeps a token made elsewhere: **New token** under Organization → Sessions in the web app (name, scope and reach picked there, shown once), or `action-platform-api tokens issue` run by an operator ([operations](start_operations.md#users-and-tokens)). The token is read from `AP_TOKEN` when set, otherwise from stdin (a hidden prompt in a terminal); it is never printed. The CLI checks it against `/api/v1/me` and writes `credentials.json` as the device flow does, so `whoami`, every remote command and `action-platform mcp --remote` use it. Changing or resetting the password revokes the account's tokens: log in again afterwards.

## Error reporting

Optional: `pip install "action-platform[sentry]"` and export `AP_SENTRY_DSN` to send CLI crashes to Sentry. Off by default — see [observability](concept_observability.md).
