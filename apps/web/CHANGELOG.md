# Changelog

## v0.6.4 — 2026-09-13

### Bug Fixes
- **web:** send the organization commit identity with every commit, with or without a code host

## v0.6.3 — 2026-09-13

### Features
- **web:** land on Activity with a review-and-merge banner after opening a pull request

### Refactoring
- **web:** drop the manual install and reset actions the API now handles itself

## v0.6.2 — 2026-09-13

### Features
- **api:** report the api component version in /api/version and Sentry; sidebar shows web, api and lib versions
- **web:** report unexpected server action failures to Sentry through one Result helper
- **web:** reset to remote from the app header when a sync is blocked by local commits

### Chores
- strip comments from the generated API client and the git hooks

## v0.6.1 — 2026-09-13

### Features
- **web:** optional Sentry reporting with the DSN read at runtime from SENTRY_DSN

### Bug Fixes
- **web:** app page offers to install the platform files instead of a 404 when the clone lost platform.toml
- **web:** drop public/icon.svg, which conflicted with the app/icon.svg favicon route

## v0.6.0 — 2026-09-13

### Features
- **web:** commit identity per organization, set in setup and settings, sent with every platform commit

## v0.5.5 — 2026-09-13

### Bug Fixes
- **web:** server actions never throw past their boundary; request errors are logged as JSON; platform git email cloud@actionplatform.io

## v0.5.4 — 2026-09-13

### Bug Fixes
- **api:** commits on the platform are authored by the signed-in user, with a platform default identity

## v0.5.3 — 2026-09-13

### Bug Fixes
- list and discard uncommitted changes in the workspace, undo release writes when the commit fails, show the sync error

## v0.5.2 — 2026-09-13

### Bug Fixes
- **web:** apps without a remembered host pick the organization's matching host before push, release and pull request

## v0.5.1 — 2026-09-13

### Bug Fixes
- **web:** release preview and run return the error instead of throwing, so production shows the cause

## v0.5.0 — 2026-09-13

### Features
- **web:** settings redesign — structured source hosts with permissions and selected repositories, roles matrix, api card, collapsible git-flow; responsive panels, dialogs and tables

## v0.4.4 — 2026-09-13

### Bug Fixes
- **web:** create the GitHub App as public so it can be installed on any organization; say so when GitHub skips the account picker
- **web:** the wizard lists every GitHub installation, disabling the ones that cannot create repositories and saying why

## v0.4.3 — 2026-09-13

### Features
- **web:** namespace choice for GitLab groups and Bitbucket workspaces when creating an app, with the same access check as GitHub

### Bug Fixes
- **gitlab:** authenticate API calls with Authorization: Bearer so OAuth tokens work, not only personal access tokens
- **web:** Connect uses OAuth authorization so every organization can connect even when the GitHub App is already installed; Install is a separate action
- **web:** GitHub App installs carry the organization in a signed state instead of relying on the session's active organization
- **web:** pick the GitHub organization from the app's installations when creating an app

## v0.4.2 — 2026-09-13

## v0.4.1 — 2026-09-13

### Bug Fixes
- **web:** GitHub install link opens the account picker even when the app is already installed elsewhere

## v0.4.0 — 2026-09-13

### Features
- **web:** repository owner per source host — set from the GitHub installation on connect, selectable in Settings
- **web:** send AP_API_TOKEN to the API from the client and the /api/v1 proxy

## v0.3.0 — 2026-09-13

### Features
- **install:** LAST_VERSION starts at 0.0.0 or at the newest tag; app header prefers the registered name
- **install:** work without a detectable language; language choice when importing from the web
- import a repository without platform.toml — install on add from the web, CLI/MCP, then commit on a branch with a pull request
- **web:** GitHub access check per host — installations, permissions and what blocks repository creation
- **templates:** any git repository can be a template source — copied as-is, platform files added when missing
- **web:** template repositories per organization, source-aware catalog, wizard, configuration and proxy

### Bug Fixes
- **templates:** a plain repository template resolves under any type; the chosen type wins
- **templates:** plain repositories get a Repositories category and resolve without a stack

## v0.2.2 — 2026-09-13

### Bug Fixes
- **api:** clone and sync private repositories with the source host credentials

## v0.2.1 — 2026-09-13

### Bug Fixes
- **web:** override postcss to 8.5.x for next (CVE-2026-45623, CVE-2026-73646)

## v0.2.0 — 2026-09-13

### Features
- **web:** teams, members, editable configuration, activity pull requests, role-gated ui
- **ui:** custom select, loader, skeletons, page transition and portal dialogs
- **web:** permissions, teams, invitations, pull request and release sync libraries
- **web:** teams, pull requests and last-synced schema with migrations 0006-0008

## v0.1.9 — 2026-09-12

### Features
- the Action Platform logo — favicon, sidebar, auth and setup pages, README

## v0.1.8 — 2026-09-12

### Features
- **web:** disconnect a connected account and remove an OAuth app

## v0.1.7 — 2026-09-12

### Bug Fixes
- **web:** accept the GitHub App install callback without state; login honours next

## v0.1.6 — 2026-09-12

### Bug Fixes
- **web:** external URLs come from PUBLIC_URL, not the container's request origin

## v0.1.5 — 2026-09-12

### Bug Fixes
- **web:** trust both schemes of the public host

## v0.1.4 — 2026-09-12

### Features
- **web:** create the GitHub App through the manifest flow — no manual OAuth app

### Chores
- strip comments from source, configs and workflows; nextCookies last

## v0.1.3 — 2026-09-12

### Bug Fixes
- **web:** run boot migrations once — in-flight promise and advisory lock
- **web:** add public/ (robots.txt) so the image build has it

## v0.1.2 — 2026-09-12

## v0.1.1 — 2026-09-12

### Features
- **web:** setup wizard, organizations › projects › apps, create-app wizard, templates catalog, code hosts, device approval
- **web:** monochrome design system — primitives, dialogs, sidebar with org switcher, brand icons
- **web:** multi-engine db (sqlite/pg/mysql), runtime config, auth with orgs/device/bearer, encrypted source hosts, oauth
- **web:** login, projects, project detail with release/deploy panels, templates, settings
- **web:** UI primitives, sidebar, page header, user menu, api-offline banner
- **web:** typed API client from OpenAPI, auth and db wiring

### Refactoring
- **core:** split into manifest, scaffold, flow and release packages; providers/source registry

### Docs
- web app and platform README — self-host, hierarchy, layout
- apps/web README and the browser section in the main README

### Build
- **web:** tailwind v4, simple-icons, better-auth plugins, per-engine drizzle configs, standalone output
- **web:** Next.js 15 app in apps/web — Tailwind v4, drizzle, better-auth, openapi-typescript

### Chores
- **platform:** declare web and api release components
- **web:** ignore tsbuildinfo
