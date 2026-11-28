# Service access

[Access control](concept_access_control.md) says what a person may do on the platform. **Service access** keeps what the same people may do on the services the team works in — the code host's organization, the CI server, error tracking, the container host — in line with their role and teams on the platform: who has what, where it drifted, and one call to give, take or remove access everywhere.

The core holds the engine and the contract. GitHub is built in: the platform manages the GitHub organization through the organization's GitHub connection. Every other service's plugin owns its service, access being one of its capabilities. A platform with no GitHub connection and no such plugin has nothing to manage.

```mermaid
flowchart LR
    P[organization: members, roles, teams] --> M[mapping]
    M --> D{diff}
    G[GitHub connection: built-in AccessProvider] --> D
    A[plugin: AccessProvider] --> D
    D -->|apply| G & A
```

## How it works

- **A grant** is `(service, account, resource, level)`: `repo/api push` on GitHub, `folder/ci build` on Jenkins. Each service names its resource kinds and orders their levels; `access_audit` lists them.
- **Live state** is read from each service on every call; nothing is cached.
- **The mapping** links each member's email to an account per service and names the grants a platform role (`roles`), a team (`teams`) or one person (`grants`) carries; the access of accounts that belong to no member (bots, agencies) is kept as found (`keep`). It is the organization's, stored once on the platform, so everyone who manages access shares it.
- **A service is imported before it is managed.** The first `access_sync` that reads a service links members to accounts (an account that is the member's email links itself; other accounts are passed as `links`), records what the service holds today and changes nothing there. A sync right after is a no-op; from then on a member who leaves the organization, changes team or role, or is granted something shows up as drift. A service that could not be read stays unimported until a later sync reads it.
- **Dry run by default.** Every change answers with the plan; `apply` makes it.
- **Never the last administrator.** Each provider refuses, before anything is sent, a change that would leave its service without an administrator.
- Accounts compare without case.

## Operations

Every route needs `org.manage` and a token that is not limited to a project or app.

| MCP tool (remote) | Command | Route | Does |
|---|---|---|---|
| `access_audit` | `action-platform access audit` | `GET /api/v1/access/audit` | drift per service, members without an account, accounts that belong to no member, the resources and levels each service grants |
| `access_who` | `action-platform access who --person <email>` / `--service <name>` | `GET /api/v1/access/who` | a person's accounts, live grants and drift; or every account on a service and the member it belongs to |
| `access_grant` | `action-platform access grant <email> <service> <resource> <level>` | `POST /api/v1/access/grant` | one grant to one person, recorded in the mapping; only that person's account is touched; the grants the service needs beside it are added |
| `access_revoke` | `action-platform access revoke <email> <service> <resource>` | `POST /api/v1/access/revoke` | takes it away; says when the role or a team still grants it |
| `access_offboard` | `action-platform access offboard <email>` | `POST /api/v1/access/offboard` | every grant of every linked account, the mapping entries, optionally the platform membership |
| `access_sync` | `action-platform access sync` | `POST /api/v1/access/sync` | imports a service the first time; then adds, changes and removes to close the drift |
| `github_branch_protection` | `action-platform github branch-protection [--repo <name>]` | `GET /api/v1/access/github/branch-protection` | per repository of the GitHub organization: default branch; whether a protection rule or an active ruleset applies to it; the ruleset rule types; required approving reviews; required status checks; whether force pushes are allowed. A repository whose protection GitHub does not return (a private repository on a plan without protection) carries the reason in `note` and null values |
| `github_repo_settings` | `action-platform github repo-settings [--repo <name>]` | `GET /api/v1/access/github/repo-settings` | per repository: visibility, default branch, archived, delete branch on merge, allow auto-merge, secret scanning, secret scanning push protection, Dependabot alerts, Dependabot security updates; a value the connection cannot see is null |

The operations run on the API, with the organization's GitHub connection, the plugins the image bundles and each plugin's options of the caller's organization — credentials stay sealed on the platform and never reach the client. The two GitHub checks only read.

**No personal token to paste.** GitHub access reads the organization's own GitHub connection under **Connect → Git** — the OAuth host first, then one added with a token — and nothing else: never the platform's environment, never another organization's connection. A plugin reads the organization's own connections the same way: the services connected under **Connect → Observability** (*Connect Sentry*, for apx-sentry). Connecting asks for the scopes the platform and the plugins need; when a connection lacks one, the audit names it and the click that grants it. A plugin's token option, where it has one, still wins when set. The CLI commands and the remote MCP tools call these routes; the local MCP server, which acts on files on one machine, has none of them.

## GitHub

The `github` service covers the organization the GitHub connection's default owner names (Connect → Git); the connected account must be an owner of it.

| Resource | Levels |
|---|---|
| `org` | `member`, `admin` — membership and role, pending invitations included |
| `team/<slug>` | `member`, `maintainer` — a team is created when a grant names one that does not exist |
| `repo/<name>` | `pull`, `triage`, `push`, `maintain`, `admin` — direct collaborators; a team's own permission on a repository is read as a grant of the account `team:<slug>` |

Accounts are GitHub logins. A team grant also brings organization membership, and the last organization admin is never removed or demoted.

| The connection is | Reading (`access_audit`, `access_who`, the checks) needs | Changing needs | Where it is granted |
|---|---|---|---|
| a GitHub App (*Create GitHub App* on the platform) | Organization *Members: Read*, Repository *Administration: Read*, the app installed on the organization | the same, *Read and write* | an app created from the platform's manifest carries them; for an older one, add them in the app's *Permissions & events* and accept the new permissions on the organization's installation |
| an OAuth App or a token | scopes `read:org` (or `admin:org`) and `repo` | `admin:org` and `repo` | *Connect GitHub* again: connecting asks for them |

When something is missing the call names it, with the links to grant it. An `apx-github` plugin still installed is not loaded: the slug `github` is reserved for the built-in service, and a provider any plugin returns under the name `github` is never used.

## Where the pieces live

| Piece | Where |
|---|---|
| The contract a plugin implements | `action_platform.abc.AccessProvider` and `Plugin.access(options)` — [writing a plugin](contribute_plugins.md#access) |
| GitHub, built in | `action_platform/providers/access/github/` (the provider and the checks); `apps/api/app/services/service_access/github.py` resolves it from the GitHub connection |
| The engine (mapping, diff, import, plan) | `action_platform/core/service_access/` |
| Which providers exist for an organization | `github` when the organization connected GitHub, and every enabled plugin whose `access(options)` returns a provider for that organization's options; one whose connection or options are incomplete shows as a failed service with the reason |
| The mapping | the plugin options table, under `access` / `mapping` for the organization — `access` is therefore not a slug a plugin can take |
| Routes | `apps/api/app/api/routes/service_access.py` |
