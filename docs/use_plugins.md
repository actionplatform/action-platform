# Plugins

A plugin — an *apx*, Action Platform extension; every package is named `apx-<slug>` — is a Python package installed next to the CLI. It can add MCP tools and CLI commands, ship cloud overlays and deploy targets, bring a release strategy or a changelog format, and replace any process of the core — git-flow rules, the releaser, the deployer, the installer, the scaffolder — with its own subclass. Everything runs in-process on the machine that installed it; the hosted platform (API, worker, web) loads nothing of the kind.

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
| Lifecycle hooks | run after a real release, deploy or pull request — never on dry runs |

The git hooks the CLI installs ask the core (`action-platform gitflow-check`) when the CLI is on `PATH`, so a plugin that changed the git-flow rules is obeyed at commit time too; without the CLI they fall back to the shell rules in `ci-scripts`. CI on the server keeps the shell rules: the repository's minimum, whatever a developer installed locally.

## On the hosted platform — the Jenkins model

With `AP_PLUGINS_DIR` pointing at a volume the API and the worker share (`deploy/dokploy/docker-compose.yml` mounts `plugins:/data/plugins`), the **Plugins** page does what the CLI does on a machine, for whoever has `org.manage`:

- **Install** a plugin the index marks `verified` — a job runs `pip install --target` into the volume, then the new plugin joins the running API and worker without a restart: its deploy targets, overlays, strategies, hooks and replaced slots are live at once. Unverified plugins cannot be installed here.
- **Enable / Disable** — at once, no restart.
- **Update** (a newer `latest`) and **Remove** — the files change on disk, but the code already loaded stays until a **Restart**: the page shows *Restart required* and a button that makes the API and the worker exit; the container's restart policy brings them back with the change. Exactly what Jenkins does with plugin upgrades.
- API and worker are separate processes; each rediscovers plugins when `plugins.json` in the volume changes.

No sandbox: an installed plugin runs inside the API and the worker with their permissions — the same trust as a Jenkins plugin, which is why only verified ones install.

## Options

A plugin keeps what it needs to remember in its own options store, WordPress-style: `surface.options.get("channel")`, `set`, `delete`, `all` — a JSON file per plugin on a machine (`~/.action-platform/plugins/<slug>.json`, or `options/` under `AP_PLUGINS_DIR`), the `plugin_option` table on the hosted platform. `GET/PUT /api/v1/plugins/{slug}/options` reads and replaces them for `org.manage`.

## Index

The web app shows the index as a marketplace under **Plugins** (search, tags, `needs`, install command to copy, which ones the hosted platform runs).

An index is a directory of `<slug>.json` files served over HTTPS — the official one is `actionplatform/plugins-index` on GitHub raw. Each file names the PyPI package, the latest version, the repository, `min_core`, a `verified` flag (someone read the code) and what the plugin `needs` (hosts it talks to, environment variables it reads — shown before you accept). Anyone can publish another index and add it with `plugin index add`.

## Trust

In-process means no sandbox: an installed plugin can do whatever the CLI's user can. The barriers are the index review (`verified`), the `needs` you read before installing, and the rule that nothing of this runs on the hosted platform. Write your own for anything company-specific; see [contribute: plugins](contribute_plugins.md).
