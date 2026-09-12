# apps/web

The Action Platform web app: Next.js 15 (App Router), better-auth, drizzle.
It talks to the Python API (`action-platform api`) — projects, git-flow,
releases, deploys — over a client generated from the API's OpenAPI schema,
so a change on the Python side is a type error here.

## Run

```bash
# terminal 1 — the API
pip install 'action-platform[api]'
action-platform api --reload           # :7788, OpenAPI at /docs

# terminal 2 — the app
cd apps/web
npm install
npm run dev                            # :3000
```

First visit opens the **setup wizard**: database (SQLite file, PostgreSQL
or MySQL — created if missing, schema migrated), first account, first
organization, code hosts. Choices land in `config/app.json` (gitignored).
Public sign-up stays closed after that.

Hosted deploys skip the database step by setting `DATABASE_URL` and
`BETTER_AUTH_SECRET` — `deploy/install.sh` does that. Pending migrations
run on boot.

## Organization › Project › App

- **Organization** — the tenant (better-auth `organization` plugin). Owns
  members and code hosts; the session carries the active one.
- **Project** — groups the apps that ship together.
- **App** — one git repository. The Python API clones it into
  `~/.action-platform/workspaces/<id>` (`/data` in Docker) and every audit,
  release and deploy runs there. *Sync* is `git fetch` + fast-forward.

## Code hosts

Settings → *Connect a code host*: **GitHub / GitLab / Bitbucket** through
OAuth. Each provider needs an OAuth app registered once (client id/secret,
callback `${PUBLIC_URL}/api/oauth/<provider>/callback`) — the dialog shows
the URL to paste. Or paste a token ("Add with a token"; *Other* covers any
git server over HTTPS).

Tokens are AES-256-GCM encrypted with a key derived from the auth secret
(`lib/crypto.ts`); GitLab and Bitbucket tokens are refreshed before use.
They are decrypted only to be sent with a push / release call to the
Python API, which authenticates git through an environment credential
helper — never `.git/config`, never a command line.

## CLI and MCP against a hosted instance

```bash
action-platform login https://platform.example.com   # opens the browser, you approve a code
action-platform whoami
action-platform mcp --remote                          # MCP tools act on the platform, not on local files
```

The login is the OAuth device flow (better-auth's `deviceAuthorization`
plugin): the CLI shows a code, the browser lands on `/device`, you approve
while signed in, the CLI receives a session token and keeps it in
`~/.action-platform/credentials.json`. Requests then hit `/api/v1/*` on
this app with `Authorization: Bearer <token>`; the route checks the
session and forwards to the Python API.

Claude Code, pointed at a VPS:

```json
{ "mcpServers": { "platform": { "command": "action-platform", "args": ["mcp", "--remote"] } } }
```

## Look

Strictly monochrome: black ground, near-black surfaces, white as the only
accent. Tokens live in `app/globals.css`; selection is a white border plus
a white circle with a black check (`components/ui/check-indicator.tsx`),
never a filled card or a colored state.

## Layout

```
app/
  setup/               first-run wizard: database → admin → organization → code hosts
  (auth)/login/        sign in
  (auth)/orgs/new/     another organization
  (app)/               everything behind a session and an active organization
    projects/                      projects of the org
    projects/[project]/            apps in a project, add by git url
    projects/[project]/apps/new/   Create project wizard: type → stack → template → configure → review
                                   (a template card in the catalog opens it at Configure)
    projects/[project]/apps/[app]/ overview, git-flow audit, commits, branches, tags,
                                   sync / push, release and deploy (dry run → dialog → run)
    templates/         catalog: search, category filters, cloud overlays
    settings/          code hosts, members, API url, git-flow rules
    device/            approve a CLI / MCP login
  api/auth/[...all]/   better-auth handler
  api/oauth/[provider]/start|callback   "Connect with …"
  api/v1/[...path]/    bearer-authenticated proxy to the Python API
components/ui/         button, card, badge, table, input, dialog, check-indicator, brand-icon
components/layout/     sidebar, page header, user menu
lib/api.ts             typed client (openapi-fetch) over lib/api.d.ts
lib/auth.ts            better-auth, lazy — rebuilt when config changes
lib/config.ts          config/app.json; env vars win
lib/db/                one connection per engine, schema/{pg,mysql,sqlite}.ts, query.ts (dialect-agnostic)
lib/orgs.ts · projects.ts · source-hosts.ts · oauth.ts · crypto.ts
drizzle/{pg,mysql,sqlite}/  migrations, applied by the wizard
```

## Regenerate the API types

```bash
npm run api:types      # builds the OpenAPI schema from the Python app, no server needed
```

Response models live in `action_platform/api/models.py`; add one there
before adding an endpoint, or the generated type is `object`.

## Schema changes

Edit all three files under `lib/db/schema/`, then:

```bash
npm run db:generate    # one migration per engine under drizzle/
```
