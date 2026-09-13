# Changelog

## v0.6.2 — 2026-09-13

### Bug Fixes
- **hooks:** keep and chain existing git hooks; honour core.hooksPath and never touch a versioned hooks directory
- **api:** refuse repositories whose symlinks escape the workspace; resolve paths before removing

### Docs
- code of conduct, contributing guide and security policy

### Tests
- unittest classes mirroring the package layout; shared builders in tests/support

## v0.6.1 — 2026-09-13

### Bug Fixes
- **manifest:** serialize user values as TOML strings and validate owner/repo before writing platform.toml

## v0.6.0 — 2026-09-13

### Features
- **web:** repository owner per source host — set from the GitHub installation on connect, selectable in Settings
- **api:** optional shared token — every route but /api/version requires Authorization: Bearer AP_API_TOKEN

### Bug Fixes
- **git:** validate branch and tag names before they reach git argv and terminate options explicitly
- **remote:** device login matches the OAuth error codes exactly, explains an expired code and retries transient network errors
- **api:** clone only https urls, optionally from ACTION_PLATFORM_GIT_HOSTS; git protocol policy per subprocess
- **api:** scope git credentials to the request with a context variable instead of mutating the process environment

### Docs
- **readme:** badges for cli, images and ci; teams, roles, template repositories and import; browser flow diagram

### Chores
- merge master into git url policy
- **settings:** drop the unused SLACK_WEBHOOK setting
- **deploy:** generate AP_API_TOKEN in install.sh, compose and the Dokploy template; document the trust boundary

## v0.5.0 — 2026-09-13

### Features
- **install:** LAST_VERSION starts at 0.0.0 or at the newest tag; app header prefers the registered name
- **install:** work without a detectable language; language choice when importing from the web
- import a repository without platform.toml — install on add from the web, CLI/MCP, then commit on a branch with a pull request
- **templates:** any git repository can be a template source — copied as-is, platform files added when missing
- **api:** template sources — merged matrix, init/cloud/service from a custom repository, remote flow and configuration tools

### Bug Fixes
- **install:** name platform.toml after the repository; skip the code-quality workflow when there is no language
- **github:** explain a 403 from a GitHub App that cannot create repositories
- **templates:** a plain repository template resolves under any type; the chosen type wins
- **templates:** detect language by manifest or source files; plain repositories without one still get platform.toml
- **templates:** plain repositories get a Repositories category and resolve without a stack
- **templates:** explain a source without index.toml

### Docs
- template repositories, remote MCP tools, edit-configuration skill

## v0.4.0 — 2026-09-13

### Features
- **api:** modular api/v1 with configuration, flow, branch-aware release and resilient sync
- the Action Platform logo — favicon, sidebar, auth and setup pages, README
- **web:** create the GitHub App through the manifest flow — no manual OAuth app
- **deploy:** Dokploy template — generated secrets and domain, one-paste import

### Bug Fixes
- **deploy:** always pull images on redeploy

### Docs
- web app teams, roles, configuration and sync
- mermaid diagrams — topology, credentials flow, data model, releases, hierarchy, wizard, mcp
- handbook under docs/ — self-hosting, web app, CLI, git-flow, platform.toml, templates, MCP, releases, architecture, development; README indexes it
- **deploy:** one-line header on the Dokploy compose
- **deploy:** compose file and steps for Dokploy

### CI
- **trivy:** fail on findings, upload sarif only on public repositories
- name the docker workflow Package Docker, grant actions:read to trivy sarif upload
- Docker Hub namespace actionplatformio

### Style
- ruff format api services and tests

### Chores
- strip comments from source, configs and workflows; nextCookies last

## v0.3.1 — 2026-09-12

### Bug Fixes
- **core:** track core/manifest — was hidden by the MANIFEST ignore rule

## v0.3.0 — 2026-09-12

### Features
- **release:** --component on the CLI, MCP and API
- **release:** components — per-path version, changelog and <name>/vX.Y.Z tags
- **remote:** device-flow login, hosted client and MCP --remote tools
- **api:** apps by git url in workspaces, init from templates, push, per-request source credentials, --reload
- **web:** typed API client from OpenAPI, auth and db wiring
- **cli:** action-platform api serves the web app's API and registers the cwd

### Refactoring
- **cli:** import from the new core packages; mcp --remote flag
- **core:** split into manifest, scaffold, flow and release packages; providers/source registry

### Docs
- releases per component
- web app and platform README — self-host, hierarchy, layout
- apps/web README and the browser section in the main README

### Tests
- **release:** component releases, root exclusion, rc counters
- **api:** registry roundtrip and read-only endpoints over a throwaway repo

### Build
- **deploy:** trim Dockerfile.api
- **deploy:** Dockerfiles, compose with optional Traefik, one-command install.sh
- **web:** tailwind v4, simple-icons, better-auth plugins, per-engine drizzle configs, standalone output
- **web:** Next.js 15 app in apps/web — Tailwind v4, drizzle, better-auth, openapi-typescript
- api extra (fastapi, uvicorn); httpx for tests

### CI
- images per component tag; PyPI only on repository releases
- mirror images to GHCR alongside Docker Hub
- publish images to Docker Hub instead of GHCR
- publish api and web images to GHCR on release tags

### Chores
- **platform:** declare web and api release components
- **platform:** align versions with 0.2.0; English __description__

## v0.2.0 — 2026-09-12

### Features
- **mcp:** prompts for new service, ship feature, release, deploy, adopt, fix git-flow; rc in gitflow_rules
- **release:** refuse existing tags before writing; rc pre-releases off main/master
- **install:** record ci in platform.toml and default to it
- **release:** sync version into pyproject, package.json and __version__

### Docs
- git-flow diagram and rules, MCP prompts
- **skills:** rc releases in start-branch and open-pull-request
- **release:** rc behaviour in tool, skill and README
- ci in platform.toml
- tagline — your platform team, as a CLI
- **pyproject:** shorter description

### Tests
- **mcp:** prompts order tools and stop before irreversible steps
- **release:** stable on main, rc increments, tag guard, same-version guard
- **install:** ci written and read from platform.toml

### Chores
- **platform:** align pyproject and __version__ with LAST_VERSION 0.1.2

## v0.1.2 — 2026-09-12

### CI
- **pypi:** fail loudly when a file already exists instead of skipping

## v0.1.1 — 2026-09-12

### Docs
- absolute cover image URL so it renders on PyPI

## v0.1.0 — 2026-09-12

### Features
- **mcp:** propose_pull_request and open_pull_request tools
- **cli:** pr command
- **pr:** propose and open pull requests from git-flow branches
- **install:** copy hooks into .git/hooks instead of a tracked .githooks
- **hooks:** bundle git hooks in the package
- dogfood devtool config + improve CLI UX
- initial devtool scaffolding

### Docs
- pr command
- **skills:** open-pull-request replaces prepare-pull-request
- **mcp:** skills and tool help reflect hooks in .git/hooks
- **cli:** help text reflects .git/hooks

### Tests
- **pr:** proposal, targets, refusals, open
- **install:** hooks land in .git/hooks and refresh from the package

### CI
- **trivy:** pin trivy-action to v0.36.0

### Chores
- **platform:** PyPI metadata and reset version before first release
- **release:** 0.1.1
- **platform:** update hooks
- untrack PLAN.md and drop reference from README

## v0.1.1 — 2026-09-12

### Chores
- **platform:** update hooks
