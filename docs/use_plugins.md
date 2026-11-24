# Plugins

A plugin — an *apx*, Action Platform extension; every package is named `apx-<slug>` — is a Python package installed next to the CLI. It can add MCP tools and CLI commands, ship cloud overlays and deploy targets, bring a release strategy or a changelog format, and replace any process of the core — git-flow rules, the releaser, the deployer, the installer, the scaffolder — with its own subclass. Everything runs in-process on the machine that installed it. The hosted platform installs nothing at runtime: its API and workers load only the plugins bundled in the image — `apx-aws-lambda` and `apx-dokploy` today, see [On the hosted platform](#on-the-hosted-platform) — and the web app none.

```bash
action-platform plugin search aws-lambda
action-platform plugin install aws-lambda     # reads the index, pip-installs into the CLI's environment, enables
action-platform plugin list
action-platform plugin disable aws-lambda     # tools refuse, overlays and targets hide, replaced slots go back to the core
action-platform plugin enable aws-lambda
action-platform plugin remove aws-lambda      # pip uninstall; a running MCP server sees it on its next start
action-platform plugin install my-thing --package apx-my-thing   # straight from PyPI, no index
action-platform plugin index add https://raw.githubusercontent.com/me/my-index/main/plugins
```

State lives in `~/.action-platform/plugins.json` (`AP_HOME` moves it): which plugins are enabled, their version and package, the indexes to search. Installing is configuration — it is a CLI (and web) matter, never an MCP tool; the agent does not install code.

## What a plugin shows up as

| It brings | Where you see it |
|---|---|
| MCP tools | `action-platform mcp` lists them as `<slug>_<name>`, with input and output schemas like the core's; a disabled plugin's tool answers `plugin <slug> is disabled` |
| CLI commands | `action-platform <slug> …` |
| Cloud overlays | `list_matrix` / `action-platform cloud set <name>`; a plugin's cloud replaces the templates repository's of the same name, since the code that deploys it lives in the plugin |
| Deploy targets, CI runners | `[deploy] target = "<name>"` in platform.toml finds them; `action-platform deploy` says which package is missing otherwise |
| Release strategy, changelog | `[release] strategy = "<name>"`, `[release] changelog = "<name>"` |
| Replaced core processes | `action-platform plugin list` shows `replaces`; `gitflow_rules`, `gitflow`, `releaser`, `deployer`, `installer`, `scaffolder` |
| Access on its service (`Plugin.access`) | the platform's `access_*` tools, `action-platform access …` and `/api/v1/access/*` cover the service once the plugin is bundled in the API image and its options are filled in — see [service access](concept_service_access.md); `plugin list` shows `access` |
| Lifecycle hooks | run after a real release, deploy or pull request — never on dry runs |

The git hooks the CLI installs ask the core (`action-platform gitflow-check`) when the CLI is on `PATH`, so a plugin that changed the git-flow rules is obeyed at commit time too; without the CLI they fall back to the shell rules in `ci-scripts`. CI on the server keeps the shell rules: the repository's minimum, whatever a developer installed locally.

## On the hosted platform

The API image bundles the plugins the platform runs: `apx-aws-lambda`, `apx-dokploy`, `apx-github`, `apx-jenkins` and `apx-sentry` are dependencies of the API, discovered through their entry points like any other. Bundling — not a marketplace — is the deliberate choice for the hosted platform: an image is reviewed and versioned as a whole, API and worker always run the same plugin code, and nothing installs or restarts at runtime. Adding a plugin to the platform is a dependency bump and a new image. `GET /api/v1/plugins` lists what the image carries (and what failed to load); a plugin's options are the only thing set at runtime, per organization.

A self-hosted platform that needs a plugin the official image does not carry builds its own `api` image on top of it — in the compose, for example:

```yaml
  api:
    image: my-ap-api:0.41.0-plugins
    pull_policy: build
    build:
      dockerfile_inline: |
        FROM actionplatformio/action-platform-api:0.41.0
        USER root
        RUN pip install --no-cache-dir apx-example==0.3.0
        USER app
```

Write the base tag literally in `FROM` and keep it equal to the `worker` and `migrate` images. A plugin's `secret` options are sealed only by an API that carries the plugin, so build the image before filling them in.

## Options

A plugin keeps what it needs to remember in its own options store, WordPress-style: `surface.options.get("channel")`, `set`, `delete`, `all` — a JSON file per plugin on a machine (`~/.action-platform/plugins/<slug>.json`; `AP_HOME` moves it), the `plugin_option` table on the hosted platform, one set per organization: `GET/PUT /api/v1/plugins/{slug}/options` reads and replaces the caller's organization's values (`org.manage`; `Remote.plugin_options` and `Remote.set_plugin_options` from the CLI side; a slug the image does not run is refused), and rows with an empty organization are platform-wide defaults an organization's values override. A deploy job carries only its organization's options.

## Index

The web app lists the plugins the platform runs under **Plugins** — one card each, the settings a plugin declares behind **Configure**; the index stays a CLI matter (`action-platform plugin search`).

An index is a directory of `<slug>.json` files served over HTTPS — the official one is `actionplatform/plugins-index` on GitHub raw. Each file names the PyPI package, the latest version, the repository, `min_core`, a `verified` flag (someone read the code) and what the plugin `needs` (hosts it talks to, environment variables it reads — shown before you accept). Anyone can publish another index and add it with `plugin index add`.

## Trust

In-process means no sandbox: an installed plugin can do whatever the CLI's user can. The barriers are the index review (`verified`), the `needs` you read before installing, and the rule that the hosted platform runs only the plugins reviewed into its image. Write your own for anything company-specific; see [contribute: plugins](contribute_plugins.md).
