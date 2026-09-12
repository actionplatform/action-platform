# The web app

`apps/web` — Next.js (App Router), better-auth, drizzle — on top of the Python API. Everything the CLI does, from a browser, for a team.

## Organization › Project › App

| Level | What it is | Owns |
|---|---|---|
| **Organization** | the tenant (better-auth `organization` plugin); the sidebar switches between the ones you belong to | members, code hosts, projects |
| **Project** | the apps that ship together (`orders-platform`) | apps |
| **App** | one git repository, cloned by the API into `~/.action-platform/workspaces/<id>` (`/data` in Docker) | git-flow audit, commits, branches, tags, releases, deploys |

## First run: the setup wizard

`/setup` opens until an organization exists.

1. **Database** — SQLite (file), PostgreSQL or MySQL. Created when missing, schema migrated, URL saved to `config/app.json`. Skipped when `DATABASE_URL` is set.
2. **Admin** — the first account. Public sign-up stays closed afterwards.
3. **Organization** — name and slug.
4. **Source hosts** — connect GitHub / GitLab / Bitbucket, or skip.

Pending migrations run on boot, so upgrading the image is enough.

## Code hosts

Settings → **Connect a code host**. Each provider needs an OAuth app registered once:

| Provider | Where | Callback |
|---|---|---|
| GitHub | Settings → Developer settings → OAuth Apps | `${PUBLIC_URL}/api/oauth/github/callback` |
| GitLab | Preferences → Applications (scopes `api write_repository read_user`) | `${PUBLIC_URL}/api/oauth/gitlab/callback` |
| Bitbucket | Workspace settings → OAuth consumers (account; repositories write/admin; pull requests write) | `${PUBLIC_URL}/api/oauth/bitbucket/callback` |

The *Set up OAuth app* dialog shows the callback URL to paste and stores the client id/secret in `config/app.json` (or read them from `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` etc.). Then **Connect with …** sends the member to the provider and comes back with a host named after the account (`GitHub · fernando`), owner defaulting to that login. GitLab and Bitbucket tokens expire and are refreshed before use.

*Add with a token* is the manual path: kind, base URL for self-hosted instances, username where the provider needs one, token, default owner. *Other* is any git server over HTTPS (push and tag only — no releases, no pull requests).

Tokens are AES-256-GCM encrypted with a key derived from `BETTER_AUTH_SECRET` and decrypted only to accompany a push / release call to the API.

## Creating an app

**Projects → project → New app**, or a template card under **Templates** (which opens the wizard at *Configure* with type, stack and template filled in).

1. **Type** — web, library, docs, plugin, empty
2. **Stack** — filtered by type
3. **Template** — the `Default` badge marks the stack's default
4. **Configure** — project name (directory and package name follow it), description, project, source host and repository owner; options: git init, CI provider, Docker overlay (when the template supports it), push to the remote
5. **Review** — summary plus the equivalent `action-platform init …` command

*Create project* generates the app into a workspace on the API, registers it, and — when *push* was on — creates the repository on the host and pushes `main`. Without push, the app page offers **Push to remote** later.

**Add an existing repository** on the project page takes a git URL; the API clones it (it must already contain a `platform.toml` — run `action-platform install` there first).

## The app page

- **Sync** (`git fetch` + fast-forward) or **Push to remote** while there is none
- git-flow audit of the current branch and its commits
- commits, remote branches with their git-flow kind, tags
- **Release**: level → *Preview* (dry run: next version and changelog) → *Release* dialog → tag, push, release on the host. Off `main`/`master` it is an `-rc.N` pre-release.
- **Deploy**: stage → *Preflight* (dry run) → *Deploy* dialog. Needs a `[deploy]` target in `platform.toml`.

Every confirmation is an in-app dialog; the UI is strictly monochrome.

## Settings

Organization members, code hosts (add, update token, remove), the API URL and the git-flow rules.

## CLI and MCP against a hosted instance

```bash
action-platform login https://platform.example.com   # device flow: approve a code at /device
action-platform whoami
action-platform mcp --remote
```

Requests go to `/api/v1/*` on the web app with `Authorization: Bearer <token>`; the route checks the session and forwards to the Python API.
