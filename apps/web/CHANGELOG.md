# Changelog

## v0.18.9 — 2026-09-15

### Bug Fixes
- **web:** failed() shows a generic message for unexpected errors and names a timeout

### Refactoring
- **web:** the app wizard split into useAppWizard, the five steps and shared parts
- **api:** GitHubAppManifestRequest and AppConfigBody — one name per meaning

### Tests
- **web:** safePath, failed, relativeTime, release helpers, run summaries, the app wizard hook

### Build
- **web:** vitest with Testing Library

## v0.18.8 — 2026-09-15

### Features
- **web:** Configuration edits the platform's copy; Export to repository writes the mirror

### Style
- **web:** escape the apostrophe

## v0.18.7 — 2026-09-15

### Features
- **web:** Releases — Create release form with name, notes and latest, Git references with commits, Release history with row actions
- **web:** release extras through the client; Textarea
- **core:** a release takes a name, Markdown notes above the commit list, and whether it is the latest
- **web:** Deployments — compact run alerts, target summary, expandable history with redeploy
- **web:** the app view knows its organization and project slugs
- **web:** status colours on badges; Hint tooltip rendered through a portal
- **api:** jobs carry version and started_at
- **web:** the Deploy card picks a release; no release, no deploy
- **web:** AWS deploy proxy url under Settings → Integrations

### Bug Fixes
- **web:** the Release card recomputes the next version after a release

### Chores
- merge master

## v0.18.6 — 2026-09-15

### Features
- **web:** Deployments tab — deploy card, target summary, list of runs
- **web:** jobs by kind with stage, dry run and author

### Refactoring
- **web:** overview shows only summary, health, commits and source

## v0.18.5 — 2026-09-15

### Features
- **web:** remove the plugins marketplace page
- **web:** drop the Plugins entry from the navigation

## v0.18.4 — 2026-09-15

### Bug Fixes
- **web:** offer the plugin update whenever latest differs from what is installed, and show both versions

## v0.18.3 — 2026-09-15

### Features
- **web:** Deploy card on the app page — stage, preflight, deploy through a worker job
- **web:** async deploy call and job polling actions

## v0.18.2 — 2026-09-15

### Bug Fixes
- **web:** a removed plugin shows Removed with no actions until the restart

## v0.18.1 — 2026-09-15

### Bug Fixes
- **plugins:** a plugin that failed to load still shows as installed with its error and can be removed

## v0.18.0 — 2026-09-15

### Features
- **web:** /.well-known served from the API
- **web:** Plugins page installs, switches, updates, removes and restarts on a hosted platform; requirements as a collapsible row

### Bug Fixes
- **web:** shorter Plugins page description
- **web:** a plugin card grows alone when its requirements open

## v0.17.0 — 2026-09-15

### Features
- **web:** Plugins marketplace — the index with search, tags, needs, install command, and what the platform runs
- **web:** overview shows the deploy target instead of an always-empty pending-changes card; pending changes become a banner when there are any

## v0.16.1 — 2026-09-15

### Features
- **web:** No CI option when installing the platform on an added repository

## v0.16.0 — 2026-09-15

### Features
- **web:** settings by category — General, People (members, teams), Integrations, Developers; import moves into Projects and Integrations; old paths redirect

## v0.15.3 — 2026-09-15

## v0.15.2 — 2026-09-15

### Bug Fixes
- **web:** forms post, so a native submit never puts a password in the URL
- **web:** allow 'unsafe-eval' in the CSP only in development so react-refresh can hydrate

## v0.15.1 — 2026-09-15

### Chores
- **web:** sync package-lock with package.json so npm ci works in the image

## v0.15.0 — 2026-09-14

### Features
- **web:** settings split into pages — General, Members, Code hosts, Git-flow, API — as a sidebar submenu and tabs on a phone

### Refactoring
- **api:** TokenMinter, ImportGateway and HostConnector.create_github_app take the last orchestration out of the routers; import schemas in schemas/imports

## v0.14.6 — 2026-09-14

### Refactoring
- **api:** routers and schemas by domain — auth, organizations, hosts, projects, apps, catalog, jobs

## v0.14.5 — 2026-09-14

### Refactoring
- **api:** routers by context (workspace, management, auth packages) over api/dependencies; AuthService and the models split by context; delete_through_host on AppRemote
- **api:** the package is app
- the API is its own package under apps/api (action_platform_api): core (abc, access, auth, db, cli, shared), api (FastAPI), repositories, services, schemas; the library no longer ships api extras or api commands; action-platform-api serve|worker|db; shared test fixtures in action_platform.testing

### Build
- **web:** regenerate package-lock

## v0.14.4 — 2026-09-14

### Bug Fixes
- **web:** settings opens for developers: invitations are only fetched by those who may manage the organization

## v0.14.3 — 2026-09-14

### Chores
- **web:** pending changes card says None / N files, Up to date / To commit

## v0.14.2 — 2026-09-14

### Chores
- **web:** every mention of clones and workspaces now speaks of pending changes and the code host
- **web:** 'Working tree' becomes 'Pending changes': the platform holds edits, not a checkout

## v0.14.1 — 2026-09-14

### Bug Fixes
- **web:** project cards show a real 'Updated' time instead of NaN years

## v0.14.0 — 2026-09-14

### Features
- **web:** pick the platform project for each selected GitHub Project

## v0.13.1 — 2026-09-14

### Bug Fixes
- **web:** not-found renders inside the app shell, so a missing project no longer breaks hydration

## v0.13.0 — 2026-09-14

### Features
- **web:** import page lists GitHub Projects and lets repositories go into one project

## v0.12.0 — 2026-09-14

### Features
- **web:** apps always live on a code host: no push button, wizard needs a host, commits and branches always push

## v0.11.3 — 2026-09-14

### Features
- **web:** import page shows what GitHub refused and how to fix it

## v0.11.2 — 2026-09-14

### Features
- **web:** import page explains why an organization is missing and links to the GitHub App install

## v0.11.1 — 2026-09-14

### Bug Fixes
- **web:** a dropped connection during a long action shows a message instead of crashing the page

## v0.11.0 — 2026-09-14

### Features
- **web:** import page: pick a GitHub host and organization, choose repositories, teams and people, follow the job

## v0.10.0 — 2026-09-14

### Features
- **web:** 'also delete the repository' option in the delete dialogs, one dialog for every app removal

## v0.9.2 — 2026-09-14

### Features
- **login:** asks for every scope and every organization by default; the device page lists all scopes as checkboxes, pre-selected and locked by the role; --scope narrows

## v0.9.1 — 2026-09-14

### Bug Fixes
- **web:** forward /api/v1 and /api/auth to the API from the middleware, reading AP_API at runtime — next.config rewrites froze the build-time default and answered 500 in the image

## v0.9.0 — 2026-09-14

### Refactoring
- **web:** catalog rendered from the API — no hard-coded types, stacks or brands; icons from the templates repository

### Chores
- **web:** regenerate the API client types

## v0.8.0 — 2026-09-14

### Features
- **core:** access catalog with labels and descriptions; Releaser.next_version and GitFlow.plan_branch previews

### Refactoring
- **web:** no rule tables left — grants from the session, labels from /api/v1/access, version and branch previews from the API, stable/protected from the branches

### Chores
- **web:** regenerate types; api:types runs the app with a database

## v0.7.2 — 2026-09-13

### Bug Fixes
- **web:** settings never crash on a host access error

## v0.7.1 — 2026-09-13

### Bug Fixes
- **web:** CSP lets the GitHub App manifest form post to github.com and Sentry start its blob worker

## v0.7.0 — 2026-09-13

### Features
- **api:** oauth_app table (0004) — OAuth apps used to connect code hosts live in the database
- **core:** access rules in Python — roles, permissions, scopes, grantable scopes and Grant

### Refactoring
- **web:** stateless — no database, secret, config file or rules; every read and write goes through /api/v1 with the caller's cookie, the API decides
- **web:** /api/v1 and /api/auth rewritten to the API; the proxy route, its helpers and the device forwarders removed
- **web:** sessions, sign-in, device approval, tokens, organizations and member accounts go through /api/auth; the web app keeps only the cookie

### Build
- **web:** drop drizzle, postgres, mysql2 and libsql
- **api:** cryptography for the source-host ciphertext
- **web:** drop better-auth

### Chores
- **web:** regenerate the API client types with the management routes
- **web:** regenerate the API client types with jobs
- **web:** regenerate the API client types with /api/v1
- **web:** regenerate the API client types with /api/auth

## v0.6.13 — 2026-09-13

### Bug Fixes
- **web:** open redirect closed, security headers, HKDF subkeys and audience on tokens, OAuth state bound to the user, timeouts on every outbound call, rate limits, explicit read rules, filtered queries, pool size via env
- **api:** refuse to start without AP_API_TOKEN unless AP_ALLOW_UNAUTHENTICATED=1; tighter CORS; proxy headers; credentials file created 0600; bearer tokens redacted from remote errors

## v0.6.12 — 2026-09-13

### Bug Fixes
- **web:** Bitbucket falls back to member workspaces, the wizard needs a workspace to publish; settings refresh on every modal close and host change

## v0.6.11 — 2026-09-13

### Bug Fixes
- **web:** settings refresh after saving an OAuth app, adding, removing or disconnecting a host
- **web:** a Bitbucket owner that is not a workspace is replaced by one — on Settings and in the wizard

## v0.6.10 — 2026-09-13

### Features
- **web:** Bitbucket Pipelines in the CI choices and labels

### Bug Fixes
- **web:** a Bitbucket connection defaults to a real workspace slug and the wizard sends the namespace it shows

## v0.6.9 — 2026-09-13

### Features
- **web:** Connect a code host as three aligned provider cards with status badges and a structured OAuth error alert

## v0.6.8 — 2026-09-13

### Features
- **web:** CI provider follows the selected source host in the wizard and the import dialog

### Bug Fixes
- **web:** send redirect_uri on the Bitbucket token exchange, which Bitbucket requires once it was sent to authorize

### Docs
- one file per context and topic (start, use, concept, contribute); real routes, tools, flags and tables; access control, API and getting started guides

## v0.6.7 — 2026-09-13

### Features
- **web:** Authorize a device as a full-page card — client, code with copy, fixed permission set, reach incl. all organizations, expiry and error states
- **web:** Connected apps shows which programs use each token
- **web:** all-organization tokens resolve the organization per request; the client name is recorded on every call
- **web:** tokens may span every organization; api_token_client records the programs using a token

### Bug Fixes
- **api:** a fetch the code host refuses fails the sync with a reason instead of a 500

## v0.6.6 — 2026-09-13

### Features
- **web:** Connected apps — your API tokens across organizations and browser sessions, with revocation
- **web:** approve a device code with scope, organization, project and app, within your role
- **web:** token reach (organization, project, app) and role-clamped scopes on /api/v1; organization directory and management endpoints
- **web:** api_token remembers the project or app a token is limited to

## v0.6.5 — 2026-09-13

### Features
- **web:** project apps as cards on mobile, stacked add-repository form
- **web:** mobile header, navigation drawer and bottom navigation below 768px
- **web:** list and revoke your API tokens in Settings
- **web:** choose the token scope when approving a device code
- **web:** scoped JWT tokens for /api/v1 — read, write, release, admin on top of the role
- **web:** api_token table

### Bug Fixes
- **web:** source hosts and template repositories laid out for phones
- **web:** every redirect to login keeps the requested path, so the device code survives sign-in

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
