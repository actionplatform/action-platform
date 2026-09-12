# apps/web

The Action Platform web app: Next.js 15 (App Router), better-auth, drizzle.
It talks to the Python API (`action-platform api`) — projects, git-flow,
releases, deploys — over a client generated from the API's OpenAPI schema,
so a change on the Python side is a type error here.

## Run

```bash
# terminal 1 — the API, from any project or none
pip install 'action-platform[api]'
action-platform api                    # :7788, registers the cwd if it has platform.toml

# terminal 2 — the app
cd apps/web
cp .env.example .env.local             # set BETTER_AUTH_SECRET
npm install
npx drizzle-kit push                   # creates data/app.db
npm run dev                            # :3000
```

First visit: sign up. Sessions are cookies; the app is guarded by
`requireSession()` in `app/(app)/layout.tsx`.

## Layout

```
app/
  (auth)/login/        sign in / sign up
  (app)/               everything behind a session
    projects/          list, register by path
    projects/[id]/     overview, git-flow audit, commits, branches, tags,
                       release and deploy panels (dry run → confirm → run)
    templates/         the init matrix
    settings/          API url, git-flow rules
  api/auth/[...all]/   better-auth handler
components/ui/         button, card, badge, table (shadcn-style, Tailwind v4)
components/layout/     sidebar, page header, user menu
lib/api.ts             typed client (openapi-fetch) over lib/api.d.ts
lib/auth.ts            better-auth + drizzle (libsql file; DATABASE_URL for hosted)
lib/db/                drizzle schema and client
```

## Regenerate the API types

With `action-platform api` running:

```bash
npm run api:types
```

Response models live in `action_platform/api/models.py`; add one there
before adding an endpoint, or the generated type is `object`.

## Actions

Release and deploy go through Next server actions (`app/(app)/projects/actions.ts`)
so the browser never calls the Python API directly. Both default to a dry
run and require a confirm before the real call.
