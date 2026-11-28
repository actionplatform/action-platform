# Platform engineering

Run an internal developer platform on your own servers, with your templates, your deploy targets and your access rules, without building it from scratch.

## Context

A platform or DevOps team supports many product teams and dozens or hundreds of repositories.

## Challenge

Building an internal platform means writing scaffolding, release tooling, deploy pipelines, access management and a portal, then maintaining all of it. Adopting a SaaS product means sending code and credentials to a vendor.

## Solution

| Need | What Action Platform provides |
|---|---|
| Run it yourself | one-command install or a Dokploy compose service; Postgres, API, worker and web app in containers; Apache-2.0 |
| Your starting points | template repositories per organization, next to the official catalog |
| Your destinations | deploy targets as plugins: Python packages with entry points, options filled per organization |
| Existing estate | import a GitHub organization's repositories, install the platform files through one pull request per repository, keep each repository's CI, read existing tags, record deploys existing pipelines make |
| Consistent rules | git-flow and branch protection with an organization default |
| Access | roles and teams on the platform; access on GitHub and other services kept in line with them, with a dry run before every change |
| Interfaces | a web app for people, a CLI for terminals and scripts, an MCP server for AI agents, a JSON API under all of them |

## Workflow

1. Install the platform and connect the code host.
2. Import the organization's repositories (**Projects → Import**), then open the install pull requests from **Adoption**.
3. Add template repositories under **Templates → Template repositories**.
4. Install the plugins you need and fill their options under **Connect → Deploy**.
5. Map roles and teams to GitHub permissions with `access_sync`, review the plan, then apply it.

## Benefits

- One place shows every app, its releases, its scopes and what runs in each.
- Changes to shared CI steps reach every repository through the versioned shared CI repositories.
- A new destination is a plugin, not a fork of the platform.
- Code stays on your code host, deploys land in your cloud account, and the database is yours.

## Related features

[Self-hosting](start_self_hosting.md) · [Adopting repositories](use_adopting.md) · [Plugins](use_plugins.md) · [Writing a plugin](contribute_plugins.md) · [Service access](concept_service_access.md) · [Templates](concept_templates.md)

## Getting started

[Self-hosting](start_self_hosting.md), then [Adopting repositories](use_adopting.md).
