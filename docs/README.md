# Action Platform documentation

Action Platform creates projects from templates, keeps every repository on the same git-flow, cuts versioned releases and deploys them to your cloud, from a web app, a CLI or an AI agent over MCP. Start with the [Introduction](start_introduction.md).

The website renders these pages at [actionplatform.io/docs](https://actionplatform.io/docs/). `index.json` in this directory lists them in reading order, with a description per page.

## Getting started

| Page | What it covers |
|---|---|
| [Introduction](start_introduction.md) | what the platform is, the problem it solves, who it is for |
| [Why Action Platform](start_why.md) | what sets it apart, and its limits |
| [Core concepts](start_concepts.md) | organization, project, app, template, release, scope, deployment and how they relate |
| [Quickstart](start_getting_started.md) | a first project, pull request and release from the CLI |

## Platform

| Page | What it covers |
|---|---|
| [Templates](concept_templates.md) | project types, stacks, cloud overlays, services, template repositories |
| [Git-flow](concept_git_flow.md) | branch kinds, commit format, hooks, CI and branch protection |
| [Releases](concept_releases.md) | versions per component, tags, changelogs |
| [Scopes](concept_scopes.md) | where a release is deployed, and which releases each scope accepts |
| [Deployments](concept_deployments.md) | targets, executors, readiness, preflight, jobs, history, rollback |
| [Cloud identity](concept_identity.md) | the platform as an OIDC issuer; AWS deploys without access keys |
| [Access control](concept_access_control.md) | roles, permissions, token scopes and reach |
| [Service access](concept_service_access.md) | access on GitHub and other services, kept in line with roles |
| [Observability](concept_observability.md) | instance health and Sentry per component |
| [Plugins](use_plugins.md) | what a plugin adds, its options, the index |

## Use cases

[Project scaffolding](usecase_scaffolding.md) · [Development standards](usecase_standards.md) · [Delivery automation](usecase_delivery.md) · [Self-service deployments](usecase_self_service.md) · [Platform engineering](usecase_platform_engineering.md)

## Guides

| Page | What it covers |
|---|---|
| [Deploy from the web](guide_first_deploy.md) | from a fresh instance to a verified deployment |
| [Deploy to AWS Lambda](guide_aws_lambda.md) | connect an AWS account, apply the overlay, deploy |
| [Add your own templates](guide_custom_templates.md) | a plain repository or a catalog as templates |
| [Adopting repositories](use_adopting.md) | import repositories, install the platform files, existing tags, CI and deploys |
| [Self-hosting](start_self_hosting.md) | `install.sh`, the compose files, Dokploy, environment, upgrades |
| [Operations](start_operations.md) | backups, restore, losing and rotating secrets |

## Reference

| Page | What it covers |
|---|---|
| [platform.toml](concept_manifest.md) | every table and key of the manifest |
| [CLI](use_cli.md) | every command, its flags and environment |
| [Web app](use_web.md) | every screen |
| [MCP](use_mcp.md) | tools, prompts and skills for AI clients |
| [API](use_api.md) | the JSON API: routes, credentials, errors |
| [Security](reference_security.md) | authentication, secrets, webhooks, cloud access |
| [Database](concept_database.md) | the database, migrations, tables, jobs |
| [Architecture](contribute_architecture.md) | packages, contexts, how a call and a deploy travel |

## Contribute

[Development](contribute_development.md) · [Writing a plugin](contribute_plugins.md)

## Resources

[Troubleshooting](start_troubleshooting.md) · [Glossary](resource_glossary.md)

## Project

| | |
|---|---|
| [Changelog](../CHANGELOG.md) · [web](../apps/web/CHANGELOG.md) · [api](../apps/api/app/CHANGELOG.md) | what changed in each release of the library and CLI, the web app and the API |
| [Contributing](../CONTRIBUTING.md) | branches, commits, pull requests, what a change must ship with |
| [Code of conduct](../CODE_OF_CONDUCT.md) | how we treat each other |
| [Security policy](../SECURITY.md) | reporting a vulnerability, what is in scope |
| [License](../LICENSE) | Apache 2.0 |
