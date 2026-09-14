# Changelog

## v0.6.1 — 2026-09-13

### Bug Fixes
- **api:** a host whose token cannot be refreshed answers ok=false on access instead of failing the request

## v0.6.0 — 2026-09-13

### Features
- **api:** /api/v1 management routes, OAuth start/callback/manifest/install, public invitation routes; X-Organization honored for members
- **api:** every write the web pages did — projects, apps, teams, members, invitations, hosts, OAuth apps, settings, template sources — plus the OAuth dance and host access checks in Python
- **api:** oauth_app table (0004) — OAuth apps used to connect code hosts live in the database
- **api:** job queue with SKIP LOCKED claims, retries and reaping; Prefer: respond-async on sync, release, deploy and push answers 202; GET /api/v1/jobs; worker runs jobs with the same services
- **api:** registry in the database (0003) shared by every instance; a missing workspace is cloned again on demand
- **api:** /api/v1 gate — caller from JWT, session or cookie; role ∩ scope ∩ reach per route; credentials and template sources filled in; apps cut to reach; imports after mutations; me, organizations, projects, teams, members, tokens and management routes
- **api:** directory, credentials and imports in Python — projects, apps, teams, members, source-host tokens decrypted (and refreshed) from the web app's ciphertext, commit identity, template sources, releases and pull requests copied from the host
- **api:** auth owned by the API — sign-up/sign-in with better-auth-compatible scrypt hashes and signed cookies, sessions, organizations and members, RFC 8628 device flow, scoped JWT tokens, per-IP rate limits

### Style
- **api:** blank lines between the steps inside functions

## v0.5.15 — 2026-09-13

### Features
- **api:** own the database — SQLAlchemy models for every web table plus job, Alembic migrations run on boot, an existing web schema is adopted, AP_DATABASE_URL and get_db

## v0.5.14 — 2026-09-13

### Bug Fixes
- **api:** refuse to start without AP_API_TOKEN unless AP_ALLOW_UNAUTHENTICATED=1; tighter CORS; proxy headers; credentials file created 0600; bearer tokens redacted from remote errors

## v0.5.13 — 2026-09-13

### Features
- Bitbucket Pipelines as a CI provider — install, wizard, import, auto-heal default to it for Bitbucket remotes

## v0.5.12 — 2026-09-13

## v0.5.11 — 2026-09-13

## v0.5.10 — 2026-09-13

### Refactoring
- **api:** services, CLI and MCP tools call Repository, GitFlow, Installer and Manifest

## v0.5.9 — 2026-09-13

### Bug Fixes
- **api:** configuration commits are made with the identity sent in the request, not only the push
- **api:** one SourceCredentials model where the token and the commit identity are each optional

## v0.5.8 — 2026-09-13

### Features
- **api:** sync moves a branch with leftover local commits to its remote, keeping uncommitted work
- **api:** put the platform files back whenever a clone is opened without platform.toml

## v0.5.7 — 2026-09-13

### Features
- **api:** report the api component version in /api/version and Sentry; sidebar shows web, api and lib versions
- **api:** sync leaves merged branches, follows rewritten remotes and accepts reset=true to match the remote

### Bug Fixes
- **core:** fast-forward before a release and roll the commit and tag back when the push is refused

## v0.5.6 — 2026-09-13

### Features
- **api:** optional Sentry reporting for the API and the CLI via AP_SENTRY_DSN

### Bug Fixes
- **api:** sync stashes local changes around the pull instead of refusing
- **api:** answer 400 instead of 500 when a clone has no platform.toml, and add POST /apps/{id}/install to write it again

## v0.5.5 — 2026-09-13

## v0.5.4 — 2026-09-13

### Bug Fixes
- **api:** commits on the platform are authored by the signed-in user, with a platform default identity

## v0.5.3 — 2026-09-13

### Bug Fixes
- list and discard uncommitted changes in the workspace, undo release writes when the commit fails, show the sync error

## v0.5.2 — 2026-09-13

## v0.5.1 — 2026-09-13

## v0.5.0 — 2026-09-13

## v0.4.3 — 2026-09-13

## v0.4.2 — 2026-09-13

### Bug Fixes
- **api:** refuse repositories whose symlinks escape the workspace; resolve paths before removing

## v0.4.1 — 2026-09-13

## v0.4.0 — 2026-09-13

### Features
- **api:** optional shared token — every route but /api/version requires Authorization: Bearer AP_API_TOKEN

### Bug Fixes
- **git:** validate branch and tag names before they reach git argv and terminate options explicitly
- **api:** clone only https urls, optionally from ACTION_PLATFORM_GIT_HOSTS; git protocol policy per subprocess
- **api:** scope git credentials to the request with a context variable instead of mutating the process environment

### Chores
- merge master into git url policy

## v0.3.0 — 2026-09-13

### Features
- import a repository without platform.toml — install on add from the web, CLI/MCP, then commit on a branch with a pull request
- **api:** template sources — merged matrix, init/cloud/service from a custom repository, remote flow and configuration tools

### Bug Fixes
- **install:** name platform.toml after the repository; skip the code-quality workflow when there is no language
- **templates:** plain repositories get a Repositories category and resolve without a stack

## v0.2.1 — 2026-09-13

### Bug Fixes
- **api:** clone and sync private repositories with the source host credentials

## v0.2.0 — 2026-09-13

### Features
- **api:** modular api/v1 with configuration, flow, branch-aware release and resilient sync

### Style
- ruff format api services and tests

### Chores
- strip comments from source, configs and workflows; nextCookies last

## v0.1.2 — 2026-09-12

## v0.1.1 — 2026-09-12

### Features
- **release:** --component on the CLI, MCP and API
- **api:** apps by git url in workspaces, init from templates, push, per-request source credentials, --reload
- **api:** JSON API over the core — projects registry, git-flow, commits, branches, tags, release and deploy

### Chores
- **platform:** declare web and api release components
