# Getting started

Two ways in: the CLI on your machine, or a hosted platform in the browser with the CLI and MCP logged in to it. Both use the same core, the same `platform.toml`, the same git-flow.

## Install

```bash
pipx install "action-platform[mcp]"     # library + CLI + MCP server for Claude Code, Codex, Cursor
```

One environment, so `action-platform mcp` always finds its extra. Running the API yourself is in [self-hosting](start_self_hosting.md).

Needs `git` and, for the source host, either the `gh` CLI or a token (`ACTION_PLATFORM_GITHUB_TOKEN`, `ACTION_PLATFORM_GITLAB_TOKEN`, `ACTION_PLATFORM_BITBUCKET_TOKEN` + `_USERNAME`).

## First project, locally

```bash
action-platform init                    # type → stack → template → name → ci; creates the repository and pushes
cd <name>
action-platform branch feature 1 hello  # develop (or main) → feature/1-hello, hooks installed
git commit -m "feat: say hello"         # the hooks refuse a message that is not Conventional Commits
action-platform pr                      # target from the rules, body from the commits
action-platform release --dry-run       # shows the next version and changelog; drop --dry-run on main to publish
```

Bring an existing repository in with `action-platform install` instead of `init`: it adds `platform.toml`, `LAST_VERSION` (the newest release tag among all the repository's tags, `v1.2.3` or `1.2.3`, a pre-release only when no stable release follows it; without tags the version the manifest declares, else the newest `CHANGELOG.md` entry; `0.0.0` when there is none; `--version` sets it), `AGENTS.md`, the quality config, the CI files and the hooks, never overwriting a file you have. The CI files are for the CI the repository already runs — `[project] ci` in an existing `platform.toml`, else a `Jenkinsfile`, `.gitlab-ci.yml`, `bitbucket-pipelines.yml` or `.github/workflows/` — and only without any of them for the remote's host; a repository with more than one needs `--ci`, and `--ci` naming another CI is applied with a warning that a second CI will run. `[source_host]` is filled for GitHub, GitLab (with `base_url` when self-hosted) and Bitbucket remotes. The whole path — many repositories, existing Jenkins or Actions deploys, tags, scopes — is in [adopting repositories](use_adopting.md).

## First project, hosted

From a fresh instance to a verified deployment. Each step names the page that has the details.

### 1. First run

Open the instance. Until an account exists `/setup` is open, and the first account needs the **setup token**: `install.sh` prints it at the end, and `docker compose exec api action-platform-api setup token` in the API container prints it again (on Dokploy, run `action-platform-api setup token` in the `ap-api` terminal). `AP_SETUP_TOKEN` replaces the derived token with one of your own. The wizard then runs **API** (checks the API is reachable), **Admin** (the first account; public sign-up stays closed, everyone else joins by invitation), **Organization** (name and slug) and **Source hosts** (connect a code host or skip). Once an account exists the token stops working and `/setup` sends anyone not signed in to `/login`. [Self-hosting › first run](start_self_hosting.md#first-run), [Web › first run](use_web.md#first-run-the-setup-wizard).

### 2. Connect a code host and the webhook

Settings → **Git**. For GitHub, *Create GitHub App* opens GitHub with the manifest filled in; confirm, install the app on the account or organization whose repositories it should manage, then connect. The app is created with *Actions: Read and write*, which the platform needs to start workflows. GitLab and Bitbucket connect with an OAuth app or *Add with a token*. [Web › Git](use_web.md#git).

Then **Webhook…** on the connected account shows the payload URL and a secret (shown once) to paste on the host: every push, pull request, release and pipeline run then syncs the app within seconds. Without it, the **Sync** button is the only way new activity arrives.

### 3. Add the app

In a project, **New app** (type, stack, template, then name, source host, repository owner, visibility) creates the repository on the host, pushes `main` and registers it; **Add an existing repository** takes a git URL. A repository without `platform.toml` opens on Configuration with `platform.toml`, the quality config, the CI files and the hooks as pending edits: **Commit changes** puts them on a `chore/<code>` branch with a pull request, and merging it is what makes the repository an installed app. Many repositories at once: **Adoption** on the project page ([adopting repositories](use_adopting.md)).

### 4. Connect CI

The app's **Settings › CI** picks the runner and the job:

| Runner | Job |
|---|---|
| **CI server** the organization added under Settings → **CI servers** (Jenkins: base URL, user, API token) | the path in the Jenkins URL: `team/app`, or `team/app/main` for a multibranch branch |
| the one embedded in the source host: GitHub Actions, GitLab CI, Bitbucket Pipelines (the host's own token, nothing to add under CI servers) | a workflow file such as `ci.yml` for GitHub Actions (empty is every workflow); nothing for GitLab and Bitbucket |

Connected, the app's **Activity › CI runs** lists the runs (**Sync** imports the latest), Overview shows the latest run of the current branch and Releases the run of each release, and **Run CI** on Overview starts the job on a branch or tag. This is the *observed* side: the platform reads what the CI does. A deploy can also be *dispatched* through CI — a workflow or Jenkins job the platform starts on a release tag — and that is declared as a deploy target, not here: [observed and dispatched deployments](concept_deployments.md#targets-and-executors).

### 5. Configure a deploy target

The platform runs a target itself through a plugin bundled in its image. Configuration → **Deploy target** applies the cloud overlay to the app (the files become pending edits and `[deploy] target` is recorded; commit them as in step 3). The plugin's settings are per organization under **Plugins** → the plugin → **Configure** ([plugins](use_plugins.md#on-the-hosted-platform)).

**AWS Lambda** (`aws/lambda`). Connect your AWS account once with the plugin's IAM-only stack and paste its `DeployRoleArn` under Plugins → AWS Lambda → Configure; no cloud key reaches the platform. The stack and the role: the [apx-aws-lambda](https://github.com/actionplatform/apx-aws-lambda) README; why it holds no key: [identity](concept_identity.md).

**Dokploy** (`dokploy`). Under Plugins → Dokploy → Configure:

| Option | What |
|---|---|
| **Dokploy URL** | where the dashboard answers, `https://dokploy.example.com` (a `[deploy] url` in the app overrides it) |
| **API key** | Settings → API Keys in Dokploy, without a rate limit |
| **Registry username**, **Registry password** | only for a private image: a GitHub token with `read:packages` for ghcr.io |

Dokploy never builds. The overlay adds a workflow that publishes `ghcr.io/<owner>/<repo>:<version>` on every published release (GitHub CI only; another CI must publish `<image>:<version>` itself); the deploy points a Dokploy application at that tag and follows it to the end. The Dokploy project is `[project] name`, the environment is the scope, the application is `<name>-<scope>`; `[deploy.domains]` gives each scope a domain and `[deploy] port`, `health`, `image` tune the rest. Every key and the requirements (Dokploy 0.20 or newer): the [apx-dokploy](https://github.com/actionplatform/apx-dokploy) README.

### 6. Create scopes

An app starts with none, and **no scope, no deploy**. The app's **Settings › Scopes** → **New scope** takes a name, a kind and a criticality. Make two:

| Scope | Kind | Criticality | Takes |
|---|---|---|---|
| `dev` | `web` | `low` | release candidates, stable and hotfix releases |
| `prod` | `web` | `high` | stable and hotfix releases only |

Criticality is the policy: `test` and `low` accept any release; `medium`, `high` and `critical` refuse a candidate. The scope's name is what the target receives as its stage (the Lambda stack is `<prefix>-<scope>`, the Dokploy environment is the scope). Kinds and the full policy: [scopes](concept_scopes.md). In a repository that deploys on its own the same scopes are `[[scopes]]` in `platform.toml`.

### 7. Release, read readiness, deploy

1. **Releases** → **New release** on `develop`: a branch other than `main`/`master` cuts a release candidate `X.Y.Z-rc.N`. **Preview changelog** is the dry run, **Create** tags, pushes and publishes it ([releases](concept_releases.md)).
2. Right after the release, the worker checks it for every scope; the release's **Timeline & readiness** page shows each scope's state, lists each check with its fix and **Re-check** runs them again. A blocked release answers a deploy with `409`; fix the check, or tick *Deploy anyway* if you may manage the organization ([readiness](concept_deployments.md#readiness)).
3. Deployments → **New deployment**: Release `X.Y.Z-rc.N`, Scope `dev`, **Run preflight** (checks only), then **Deploy to dev**. The deploy log follows the worker.
4. Merge to `main`, then **New release** there for the stable `X.Y.Z`, and deploy it to `prod`. A candidate aimed at `prod` is refused by the `scope.release-shape` check.

### 8. See the deployment

The Deployments tab lists every deploy with its status. A deployment moves `queued` → `running` → `success` and then **verified**, once the platform has checked the destination for that exact version ([verified at the destination](concept_deployments.md#verified-at-the-destination)). `success` without `verified` means the pipeline ended but the version is not there. A row opens the run, the endpoint and the log; **Redeploy** repeats it, and deploying an older release is the rollback.

### The same, from the terminal

Inside the project's repository, with the plugin's settings in the environment (`DOKPLOY_URL`, `DOKPLOY_API_KEY`) or its options file:

```bash
action-platform plugin install dokploy   # once; aws-lambda for aws/lambda
action-platform cloud set dokploy        # the overlay; commit it through a pull request
action-platform scopes                   # [[scopes]] of platform.toml: name, kind, criticality
action-platform release --dry-run        # on develop: the next X.Y.Z-rc.N and its changelog
action-platform release
action-platform readiness --version 1.4.0-rc.1 --scope dev
action-platform deploy --version 1.4.0-rc.1 --scope dev
action-platform deployments --sync       # what arrived at each target, verified or not
```

`scopes` only reads the manifest: write `[[scopes]]` into `platform.toml` (see [scopes](concept_scopes.md#cli-and-mcp)), or create them on the platform from the web or the `create_scope` tool. `readiness` exits `1` when something blocks; `deploy` runs the target from your machine, and `deployments` reads the hosted platform after `login`.

Point the CLI and an AI agent at the hosted platform:

```bash
action-platform login https://<platform> --scope read,write   # approve the code in the browser, choose where the token may act
action-platform whoami
action-platform mcp --remote                                   # the same tools, acting on the hosted apps
```

With that token the agent can do the web steps above — `create_scope`, `release_readiness`, `deploy` and `list_deployments` among the remote tools. What a token may do is your role narrowed by its scope and reach — [access control](concept_access_control.md).

## Next

[adopting](use_adopting.md) for repositories you already have · [CLI](use_cli.md) for every command · [web](use_web.md) for every screen · [MCP](use_mcp.md) for agents · [manifest](concept_manifest.md) for `platform.toml` · [self-hosting](start_self_hosting.md) to run your own.
