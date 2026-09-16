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

The rules are code in the library, applied by the API in front of every call, which answers 403 naming the missing permission. The web app holds no copy: it reads the table from the API to hide or disable what the role lacks.

## Scopes

Chosen when a device code is approved — `action-platform login` asks for every scope unless `--scope` narrows it; the page pre-selects what the role allows — and stored on the token.

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

`action-platform login` mints a signed token carrying user, organization, scope and reach. Valid 90 days, 30 with the `admin` scope; revoking it on the Sessions page invalidates it on the next request. The platform records which program used it — the MCP server reports its client (Claude Code, Codex, Cursor…) on every call.

**Connected apps** (key icon next to your name) lists your tokens across organizations with scope, reach and the programs using them, plus your browser sessions; both can be revoked there. The rules on this page are applied by the API when it approves a device, issues a token or verifies one — the web app only displays them.

## Commit identity

Commits the platform makes (releases, configuration changes) use the organization's commit identity — Settings → **Commit identity**, default `Action Platform <cloud@actionplatform.io>` — sent with every request that may commit. The API's `AP_GIT_AUTHOR_*` apply only when nothing arrives.

See also: [web app](use_web.md) for the screens, [CLI](use_cli.md) for `login`, [MCP](use_mcp.md) for `whoami` and the organization tools, [architecture](contribute_architecture.md) for how credentials travel.
