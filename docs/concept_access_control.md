# Access control

Who may do what, in one place: **roles** say what a person can do in an organization, **scopes** say what a token may do on that person's behalf, **reach** says where. A request through `/api/v1` passes only when all three agree; the web app checks the role alone (a browser session has no token).

## Roles

Assigned per organization under Settings → **Members**.

| Role | Permissions |
|---|---|
| `owner` | everything; at least one per organization, the last one cannot be demoted |
| `admin` | `org.manage`, `project.manage`, `app.release`, `app.configure`, `app.flow`, `app.sync` |
| `deployer` | `app.release`, `app.configure`, `app.flow`, `app.sync` |
| `developer` | `app.configure`, `app.flow`, `app.sync` |
| `viewer` | read only |

| Permission | Grants |
|---|---|
| `org.manage` | members, invitations, teams, source hosts, commit identity, settings |
| `project.manage` | create and delete projects, add and remove apps |
| `app.release` | create releases |
| `app.configure` | edit `platform.toml`, deploy target and services, install the platform files, commit the changes |
| `app.flow` | start branches, check out, push, open pull requests |
| `app.sync` | sync the workspace with the source host |

Source: `apps/web/lib/permissions.ts`. Server actions check a permission before acting; the UI hides or disables what the role lacks; `/api/v1` answers 403 naming the missing permission.

## Scopes

Chosen when a device code is approved (`action-platform login … --scope`), stored on the token.

| Scope | Unlocks |
|---|---|
| `read` | always present: list projects, apps, releases, branches, activity |
| `write` | `app.configure`, `app.flow`, `app.sync` |
| `release` | `app.release` |
| `admin` | `project.manage`, `org.manage` |

A scope never widens a role: a `developer` with a `release` token still cannot release, an `owner` with a `read` token can only look. The approval page offers only the scopes the role can grant in the chosen organization, and `POST /api/v1/tokens` clamps the request the same way.

## Reach

Also chosen at approval.

| Reach | Effect on `/api/v1` |
|---|---|
| one organization | every call acts there; the role is that organization's |
| **all organizations** | the role is checked in the organization each call touches — the app's own for app routes, `X-Organization: <id or slug>` (or `?organization=`) for organization-level routes; `GET /apps` and `GET /projects` answer across all of them |
| one project | only that project's apps are visible; the token cannot add apps or manage the organization |
| one app | only that app |

## Tokens

`action-platform login` mints a JWT (`HS256`, signed with `BETTER_AUTH_SECRET`) carrying user, organization, scope and reach; its `jti` is a row in `api_token`, so revoking the row invalidates the token on the next request. Valid 90 days. `api_token_client` records which program used it — the MCP server reports its client (`clientInfo`: Claude Code, Codex, Cursor…) on every call.

**Connected apps** (key icon next to your name) lists your tokens across organizations with scope, reach and the programs using them, plus your browser sessions; both can be revoked there.

## Commit identity

Commits the platform makes (releases, configuration changes) use the organization's commit identity — Settings → **Commit identity**, default `Action Platform <cloud@actionplatform.io>` — sent with every request that may commit. The API's `AP_GIT_AUTHOR_*` apply only when nothing arrives.

See also: [web app](use_web.md) for the screens, [CLI](use_cli.md) for `login`, [MCP](use_mcp.md) for `whoami` and the organization tools, [architecture](contribute_architecture.md) for how credentials travel.
