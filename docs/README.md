# Documentation

Action Platform standardizes how a project is born, versioned and shipped — from a template or an existing repository, through git-flow, to a release and a deploy — from the CLI, from a web app, or through an AI agent over MCP.

## Where to start

| I want to… | Read |
|---|---|
| install it and ship a first project | [Getting started](start_getting_started.md) |
| run the platform for my team | [Self-hosting](start_self_hosting.md) |
| know what a screen, command or tool does | [Web](use_web.md) · [CLI](use_cli.md) · [MCP](use_mcp.md) · [API](use_api.md) |
| understand who may do what | [Access control](concept_access_control.md) |
| change or extend the code | [Architecture](contribute_architecture.md) · [Development](contribute_development.md) |

## All guides

**Start** — install and run

| | |
|---|---|
| [Getting started](start_getting_started.md) | install, first project locally or hosted, point the CLI and an agent at a platform |
| [Self-hosting](start_self_hosting.md) | `install.sh`, the compose files, Dokploy, environment, upgrades, backups |

**Use** — one guide per surface

| | |
|---|---|
| [Web](use_web.md) | organizations › teams › projects › apps, setup wizard, source hosts, creating apps, releases, settings, connected apps |
| [CLI](use_cli.md) | every command, its flags and environment |
| [MCP](use_mcp.md) | tools, prompts and skills for AI clients — locally or against a hosted platform |
| [API](use_api.md) | the JSON API behind the web app: routes, credentials contract, trust, errors |

**Concept** — the model, one term per guide

| | |
|---|---|
| [Access control](concept_access_control.md) | roles, permissions, token scopes and reach, commit identity |
| [Git-flow](concept_git_flow.md) | branch kinds, commit format, what the hooks and CI refuse |
| [Manifest](concept_manifest.md) | `platform.toml`, the file that declares a project |
| [Templates](concept_templates.md) | project types, stacks, cloud overlays, services; adding your own repositories |
| [Releases](concept_releases.md) | versions per component, tags, what each one publishes |
| [Observability](concept_observability.md) | Sentry per component: variables, what is sent, what is not |
| [Database](concept_database.md) | the one database web and API share: connecting the API, migrations, adopting an existing schema, the tables |

**Contribute** — how it is built

| | |
|---|---|
| [Architecture](contribute_architecture.md) | packages, the objects in the core, providers, how credentials travel, the web app's data |
| [Development](contribute_development.md) | running everything locally, tests, regenerating the API client |

## Project

| | |
|---|---|
| [Changelog](../CHANGELOG.md) · [web](../apps/web/CHANGELOG.md) · [api](../action_platform/api/CHANGELOG.md) | what changed in each release of the library and CLI, the web app and the API |
| [`LAST_VERSION`](../LAST_VERSION) · [web](../apps/web/LAST_VERSION) · [api](../action_platform/api/LAST_VERSION) | the current version of each component — the same files `action-platform release` bumps |
| [Contributing](../CONTRIBUTING.md) | branches, commits, pull requests, what a change must ship with |
| [Code of conduct](../CODE_OF_CONDUCT.md) | how we treat each other |
| [Security](../SECURITY.md) | reporting a vulnerability, what is in scope |
| [License](../LICENSE) | Apache 2.0 |

## Glossary

| Term | Means |
|---|---|
| organization › project › app | the hierarchy; an app is one git repository |
| workspace | the platform's clone of an app, where it commits, releases and syncs |
| source host | GitHub, GitLab, Bitbucket or a generic remote, connected per organization |
| template source | a repository of templates; the official one plus any the organization adds |
| token · scope · reach | what `action-platform login` mints; what it may do; where |
| release · component | a version cut from the repository; `web`, `api` and the library each have their own |
