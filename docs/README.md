# Documentation

Files are named `<context>_<topic>.md`: **start** (install and run), **use** (one per surface: web, CLI, MCP, API), **concept** (the model — one term per file) and **contribute** (how it is built). Terms used everywhere: *organization › project › app*; *workspace* — the platform's clone of an app; *source host* — GitHub, GitLab, Bitbucket or a generic remote; *template source* — a templates repository; *token · scope · reach*; *release · component*.

**Start**

| | |
|---|---|
| [Getting started](start_getting_started.md) | install, first project locally or hosted, point the CLI and an agent at a platform |
| [Self-hosting](start_self_hosting.md) | `install.sh`, the compose files, Dokploy, environment, upgrades, backups |

**Use**

| | |
|---|---|
| [Web](use_web.md) | organizations › teams › projects › apps, setup wizard, source hosts, creating apps, releases, settings |
| [CLI](use_cli.md) | every command, its flags and environment |
| [MCP](use_mcp.md) | tools, prompts and skills for AI clients — locally or against a hosted platform |
| [API](use_api.md) | the JSON API behind the web app: routes, credentials contract, errors |

**Understand**

| | |
|---|---|
| [Access control](concept_access_control.md) | roles, permissions, token scopes and reach, commit identity |
| [Git-flow](concept_git_flow.md) | branch kinds, commit format, what the hooks and CI refuse |
| [Manifest](concept_manifest.md) | `platform.toml`: the file that declares a project |
| [Templates](concept_templates.md) | project types, stacks, cloud overlays, services; adding your own repositories |
| [Releases](concept_releases.md) | versions per component, tags, what each one publishes |
| [Observability](concept_observability.md) | Sentry per component: variables, what is sent, what is not |

**Contribute**

| | |
|---|---|
| [Architecture](contribute_architecture.md) | packages, the objects in the core, providers, how credentials travel, the web app's data |
| [Development](contribute_development.md) | running everything locally, tests, regenerating the API client |
