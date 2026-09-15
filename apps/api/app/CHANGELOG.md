# Changelog

## v0.20.12 — 2026-09-15

## v0.20.11 — 2026-09-15

### Breaking Changes
- **api:** plugins are bundled in the image — no runtime install, remove, switch or restart; GET /api/v1/plugins lists what the image carries, options stay per organization

## v0.20.10 — 2026-09-15

### Refactoring
- **api:** DirectoryService dissolved — OrganizationRepository, ProjectsRepository, IntegrationsDirectory, and the two compositions that span them (AccessDirectory, ImportDirectory)
- **api:** repositories by context — the directory's query mixins become repositories/{organization,projects,integrations}; workspace and configuration folders
- **api:** schemas and models named by context; routes import from the owning module
- **api:** services/integrations (hosts, plugins), services/organization (sessions), services/auth out of core
- **api:** services/projects (service, apps, organization_import) and services/templates
- **api:** services by context — activity, releases, deployments, configuration
- **api:** job kinds registered through services/jobs/registry; the worker lives in services/jobs
- **api:** routers become api/routes — one file per context, deployments apart from releases

### CI
- contracts for the layout by context — routes → services → repositories → schemas → core; independent app contexts; git_auth leaves core

## v0.20.9 — 2026-09-15

### Features
- **api:** domain errors with a status — ServiceError family — mapped at the API boundary
- **api:** migrations move to the deploy — AP_DATABASE_AUTO_MIGRATE, advisory lock, readiness on /api/version
- **api:** platform admins (AP_PLATFORM_ADMINS) — the role that changes the platform itself

### Bug Fixes
- **api:** plugin options belong to an organization over platform defaults; plugin lifecycle needs a platform admin

### Performance
- **api:** request bodies capped at 2 MB; app listings filtered in the service instead of re-parsing the response
- **api:** the gate's database work runs off the event loop and the host import becomes a worker job

### Refactoring
- **api:** routers import schemas from the module that owns them
- **api:** hosts split into reads and writes; catalog sources apart from the service
- **api:** GitHubAppManifestRequest and AppConfigBody — one name per meaning
- **api:** the CLI entry points move out of core — core imports no services
- **api:** PluginsCatalog leaves the templates catalog
- **api:** the gate keeps ASGI; Planner, Authorizer and Dispatcher decide the call
- **api:** Worker claims and dispatches; JobHandlers, JobContext, DeployEnv and AppIdentity own the rest; the registry is injected
- **api:** CommitService — committing, branching and the pull request leave ConfigurationService
- **api:** ConfigStore injected into the services that read the app's configuration
- **api:** Registry keeps rows; Workspaces.adopt validates, clones and registers
- **api:** services raise domain errors, never HTTPException

### Chores
- merge master
- merge master
- merge master
- merge master
- merge master

## v0.20.8 — 2026-09-15

### Features
- **api:** services read the app's configuration from the platform; manifest edits save there and export writes the mirror
- **api:** app_config table and ConfigStore — the platform keeps the configuration, seeded from the clone's platform.toml

## v0.20.7 — 2026-09-15

### Features
- **api:** branches carry their latest commit sha
- **api:** name, notes and latest on ReleaseRequest
- **api:** jobs carry version and started_at
- **api:** version on DeployRequest
- **api:** deploy jobs carry AP_APP and every plugin option as AP_<SLUG>_<KEY>

### Chores
- merge master

## v0.20.6 — 2026-09-15

### Features
- **api:** jobs list filters by kind and says stage, dry run and who asked

## v0.20.5 — 2026-09-15

## v0.20.4 — 2026-09-15

### Features
- **api:** identity tokens carry the caller's scopes

## v0.20.3 — 2026-09-15

### Bug Fixes
- **api:** plugin removal marks the row removed and the catalog reports it

## v0.20.2 — 2026-09-15

### Bug Fixes
- **plugins:** a plugin that failed to load still shows as installed with its error and can be removed

## v0.20.1 — 2026-09-15

### Bug Fixes
- **plugins:** a plugin loads on an install without the mcp extra — action_platform.mcp imports without the SDK; a load failure names its cause

## v0.20.0 — 2026-09-15

### Features
- **api:** the platform as an OIDC issuer — discovery, JWKS, tokens per deploy from the worker and for logged-in callers
- **api:** plugins the Jenkins way — install verified plugins into the volume without a restart, enable/disable, update and remove with a restart, options table

## v0.19.0 — 2026-09-15

### Features
- **api:** GET /api/plugins — the plugins index plus which plugins this platform runs
- **core:** every process is a class in a wiring slot — gitflow_rules, gitflow, releaser, deployer, installer, scaffolder — so a plugin can replace it with a subclass

## v0.18.5 — 2026-09-15

## v0.18.4 — 2026-09-14

### Features
- **env:** a .env in the working directory fills in unset variables for the CLI, the API and the worker; api errors print one line

## v0.18.3 — 2026-09-14

### Refactoring
- **api:** TokenMinter, ImportGateway and HostConnector.create_github_app take the last orchestration out of the routers; import schemas in schemas/imports

## v0.18.2 — 2026-09-14

### Refactoring
- **api:** routes only translate HTTP — ProjectService (add, init, delete, sync activity) and HostConnector (OAuth finish) hold the orchestration
- **api:** routes declare their dependencies as Annotated types (CallerDep, OrgDep, WritesDep, …)

## v0.18.1 — 2026-09-14

### Refactoring
- **api:** routers and schemas by domain — auth, organizations, hosts, projects, apps, catalog, jobs

## v0.18.0 — 2026-09-14

### Refactoring
- **api:** routers by context (workspace, management, auth packages) over api/dependencies; AuthService and the models split by context; delete_through_host on AppRemote

## v0.17.1 — 2026-09-14

### Refactoring
- **api:** core never imports services (caller and enrich live in services/access), core/auth is a real package, one ruff config for the whole repository

## v0.17.0 — 2026-09-14

### Refactoring
- **api:** the package is app

## v0.16.0 — 2026-09-14

### Refactoring
- **api:** services as structured classes — HostProvider per code host (OAuth, refresh, access), import steps as classes, MatrixView, TemplateRepos, AppManifest, GitUrl, HttpClient, Clones; every __init__ only re-exports

## v0.15.1 — 2026-09-14

### Refactoring
- **api:** every service in a package — workspace, catalog, jobs, shared; ImportSource and HostDirectory ABCs behind imports and github_import

## v0.15.0 — 2026-09-14

### Features
- **api:** app detail and next-version report 0.0.0 for untagged repositories

### Refactoring
- **api:** services split into packages — directory (one module per domain), hosts (oauth and providers), imports (per provider), apps (inventory, generate, remote); common and credentials helpers

## v0.14.1 — 2026-09-14

### Features
- **api:** projects answer created_at and updated_at (latest of the project and its apps)

## v0.14.0 — 2026-09-14

### Features
- **import:** a GitHub Project can land in an existing platform project

## v0.13.2 — 2026-09-14

### Bug Fixes
- **workspace:** refresh origin/HEAD and check the branch exists before falling back to it

## v0.13.1 — 2026-09-14

## v0.13.0 — 2026-09-14

### Features
- **api:** import request takes projects and a target project
- **import:** GitHub Projects become projects with their linked repositories as apps; repositories can go into one chosen project

## v0.12.1 — 2026-09-14

### Bug Fixes
- **import:** a refused repository listing is reported with the fix instead of failing the preview

## v0.12.0 — 2026-09-14

### Features
- **api:** nothing local survives: init pushes at once, commits and branches push, checkout is a registry field, edits are drafts
- **api:** disposable clones: rebuilt from the remote when missing, leveled with it before use, drafts written on top
- **db:** checked-out branch per app and pending edits (draft table); workspaces under the temp dir

## v0.11.3 — 2026-09-14

### Bug Fixes
- **import:** ask GitHub Apps for the members permission; preview reports what GitHub refused instead of failing

## v0.11.2 — 2026-09-14

### Bug Fixes
- **import:** list organizations from memberships, /user/orgs and GitHub App installations; answer the app's install url

## v0.11.1 — 2026-09-14

### Bug Fixes
- **db:** pool of 10 with 20 overflow by default, both configurable

### Performance
- **registry:** look one app up by id instead of loading every row

## v0.11.0 — 2026-09-14

### Features
- **api:** /import/github preview endpoints and the import_github job
- **api:** github import service: organizations, repositories, teams and people from a connected host

## v0.10.0 — 2026-09-14

### Features
- **api:** deleting an app or a project can also delete its repositories on the host

## v0.9.0 — 2026-09-14

### Features
- **catalog:** revalidate the templates index with its ETag every minute instead of caching it ten

## v0.8.1 — 2026-09-14

## v0.8.0 — 2026-09-14

### Features
- **api:** GET /api/matrix answers the catalog from the templates repository's raw index.json (cached, clone as fallback), icons as absolute URLs, types and stacks included

## v0.7.0 — 2026-09-14

### Features
- **api:** GET /api/v1/access, /apps/{id}/next-version, /apps/{id}/branches/plan; branches carry stable

## v0.6.3 — 2026-09-14

### Refactoring
- **api:** the registry lives only in the database — apps.json imported once and renamed, no file fallback; the API refuses to start without AP_DATABASE_URL

## v0.6.2 — 2026-09-13

### Bug Fixes
- **api:** apps still only in apps.json are adopted into the registry table on boot

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
