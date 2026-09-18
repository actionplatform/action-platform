# Documentation

Action Platform standardizes how a project is born, versioned and shipped — from a template or an existing repository, through git-flow, to a release and a deploy — from the CLI, from a web app, or through an AI agent over MCP.

## Where to start

| I want to… | Read |
|---|---|
| install it and ship a first project | [Getting started](start_getting_started.md) |
| run the platform for my team | [Self-hosting](start_self_hosting.md) |
| understand what happens when I deploy | [Deployments](concept_deployments.md) · [Identity](concept_identity.md) |
| know before deploying whether a release will make it | [Deployments › readiness](concept_deployments.md#readiness) |
| fix something that was refused | [Troubleshooting](start_troubleshooting.md) |
| know what a screen, command or tool does | [Web](use_web.md) · [CLI](use_cli.md) · [MCP](use_mcp.md) · [API](use_api.md) · [Plugins](use_plugins.md) |
| understand who may do what | [Access control](concept_access_control.md) |
| change or extend the code | [Architecture](contribute_architecture.md) · [Development](contribute_development.md) · [Writing a plugin](contribute_plugins.md) |

## All guides

**Start** — install and run

| | |
|---|---|
| [Getting started](start_getting_started.md) | install, first project locally or hosted, point the CLI and an agent at a platform |
| [Self-hosting](start_self_hosting.md) | `install.sh`, the compose files, Dokploy, environment, upgrades, backups |
| [Troubleshooting](start_troubleshooting.md) | every message the platform refuses with, what it means, what to do |

**Use** — one guide per surface

| | |
|---|---|
| [Web](use_web.md) | one section per screen: setup, projects and apps, the app's tabs, templates, import, organization, plugins, settings |
| [CLI](use_cli.md) | every command, its flags and environment |
| [MCP](use_mcp.md) | tools, prompts and skills for AI clients — locally or against a hosted platform |
| [Plugins](use_plugins.md) | what a plugin adds or replaces, its options, how the hosted platform bundles them |
| [Identity](concept_identity.md) | the platform as an OIDC issuer and the AWS deploy proxy: deploys without cloud access keys, apps registered on their first deploy |
| [API](use_api.md) | the JSON API behind the web app: routes, credentials contract, trust, errors |

**Concept** — the model, one term per guide

| | |
|---|---|
| [Access control](concept_access_control.md) | roles, permissions, token scopes and reach, commit identity |
| [Git-flow](concept_git_flow.md) | branch kinds, commit format, what the hooks and CI refuse |
| [Manifest](concept_manifest.md) | `platform.toml`, the file that declares a project |
| [Templates](concept_templates.md) | project types, stacks, cloud overlays, services; adding your own repositories |
| [Releases](concept_releases.md) | versions per component, tags, what each one publishes |
| [Deployments](concept_deployments.md) | stages, targets, readiness, preflight, the deploy job, history, redeploy, tearing down |
| [Observability](concept_observability.md) | Sentry per component: variables, what is sent, what is not |
| [Database](concept_database.md) | the one database web and API share: connecting the API, migrations, adopting an existing schema, the tables |

**Contribute** — how it is built

| | |
|---|---|
| [Architecture](contribute_architecture.md) | packages, the objects in the core, providers, how credentials travel, the web app's data |
| [Development](contribute_development.md) | running everything locally, tests, regenerating the API client |

## Project

`index.json` in this directory lists the guides in reading order; the website's Docs pages read it and the markdown files straight from this repository.

| | |
|---|---|
| [Changelog](../CHANGELOG.md) · [web](../apps/web/CHANGELOG.md) · [api](../apps/api/app/CHANGELOG.md) | what changed in each release of the library and CLI, the web app and the API |
| [`LAST_VERSION`](../LAST_VERSION) · [web](../apps/web/LAST_VERSION) · [api](../apps/api/app/LAST_VERSION) | the current version of each component — the same files `action-platform release` bumps |
| [Contributing](../CONTRIBUTING.md) | branches, commits, pull requests, what a change must ship with |
| [Code of conduct](../CODE_OF_CONDUCT.md) | how we treat each other |
| [Security](../SECURITY.md) | reporting a vulnerability, what is in scope |
| [License](../LICENSE) | Apache 2.0 |

## Glossary

| Term | Means |
|---|---|
| organization › project › app | the hierarchy; an app is one git repository |
| team | a group of organization members that looks after projects; a project belongs to at most one |
| workspace | the platform's disposable clone of an app, rebuilt from the remote whenever a request needs its files |
| pending edits | changes the platform holds for an app (rows in `draft`), written onto the clone until **Commit changes** or **Discard changes** |
| source host | GitHub, GitLab, Bitbucket or a generic remote, connected per organization under Settings → Git |
| manifest | `platform.toml`, the file that declares a project: type, language, git-flow rules, `[deploy]` |
| template · overlay | a project skeleton (type › stack › template); an overlay adds a cloud or Docker on top of it |
| template source | a repository of templates; the official one plus any the organization adds |
| release · component | a version cut from the repository (tag, changelog, release on the host); `web`, `api` and the library each have their own |
| deploy target | where an app goes (`aws/lambda`, `docker`…), declared under `[deploy]` and implemented by a plugin |
| stage | an environment of an app, `dev` or `prod`; one stack, one history and one deploy at a time each |
| preflight | a deploy's checks without the deploy (`dry_run`) |
| job | queued work the worker runs — sync, release, readiness, deploy, destroy, import; what Deployment history lists |
| readiness | whether a release can reach a stage, checked per stage after every release without building; a blocked stage refuses the deploy unless forced |
| plugin · option | a package that adds targets, overlays and tools; an option is a setting it declares, filled per organization under Plugins |
| deploy proxy | the Lambda in an AWS account that turns the platform's identity token into credentials for one app |
| identity token | the short-lived JWT the platform signs about an app for a deploy; what the cloud trusts instead of a key |
| token · scope · reach | what `action-platform login` mints; what it may do; where (organizations, a project, an app) |
| role · permission | owner, admin, deployer, developer, viewer; the six things a role may do in an organization |
| git-flow | the branch kinds, the base each starts from, the Conventional Commit format the hooks and CI enforce |
