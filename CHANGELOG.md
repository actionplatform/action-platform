# Changelog

## v0.26.0 — 2026-09-19

### Features
- **scopes:** a scope is a name, a kind and a criticality — and no scope, no deploy

## v0.25.0 — 2026-09-18

### Features
- **web:** scopes — the app's scopes, New scope, and a deploy that lands on a scope
- **api:** scopes — where an app's releases are deployed, and what each accepts
- **scopes:** scopes in the core — where a release is deployed, with a kind and a criticality
- **organization:** an owner can delete the organization

### Bug Fixes
- **api:** the app list reads the snapshot, not the clone

### Docs
- **scopes:** no latest left in prose or diagram
- **scopes:** any stable release serves any scope — no latest rule
- **scopes:** test accepts any release
- **scopes:** a stable release serves any scope
- architecture decisions move to the strategy repository
- **scopes:** mermaid labels quoted, fence closed
- **scopes:** mermaid diagrams — the model, what each criticality accepts, the gate, the data model, the rollout
- **adr:** the criticality table in ADR 0009
- **scopes:** a hotfix release may be deployed to any scope
- **scopes:** only the rules asked for — release shape and latest by criticality; no approvals, no promotion ladder
- **scopes:** an app has any number of scopes, each with its own kind and criticality
- **scopes:** the strategy — a deploy lands on a scope whose criticality decides which releases it takes

## v0.24.0 — 2026-09-18

### Features
- **plugins:** every plugin's logger reaches the job log

### Tests
- **insights:** pin the clock at noon so the day's counts do not straddle midnight UTC

### Build
- **api:** apx-aws-lambda 0.4.0 — sam output streams to the job log

## v0.23.0 — 2026-09-18

### Features
- **logs:** every line a job writes is stored as it happens and can be followed live

### Docs
- **readme:** readiness, tracked deployments, CI and the dashboard in the front door

### Build
- **api:** apx-aws-lambda 0.3.11 — the aws/lambda readiness checks

## v0.22.0 — 2026-09-18

### Features
- **readiness:** a release knows whether it can reach a stage before anyone deploys it
- **web:** phones get cards instead of tables, stacked toolbars and footers, wrapping rows

### Bug Fixes
- one label for a person — the display name, the email only when there is none
- **deploy:** the worker image builds native gems and wheels

### Docs
- release readiness — the concept, the API, the CLI, the web, the plugin contract and ADR 0008

### Build
- **api:** apx-aws-lambda>=0.3.9 — a ROLLBACK_COMPLETE stack no longer blocks the deploy

## v0.21.0 — 2026-09-18

### Features
- a timeline per release and a dashboard for the organization
- **ci:** GitLab CI and Bitbucket Pipelines as embedded runners; Run from the CI tab
- webhooks from the code host trigger the sync

### Performance
- **api:** reads come from a snapshot; GET routes never touch git
- **api:** the queue wakes workers with LISTEN/NOTIFY
- **api:** indexes on every listing, a worker that runs jobs side by side, an API with several processes

### Refactoring
- **web:** members, teams and template repositories on DataTable; Deploy target and Services on ActionForm
- **remote:** the answer models live with the remote client and are checked against the API's OpenAPI

### Docs
- **adr:** the decisions of this week — release table, targets and executors, snapshot reads, server pages, DataTable, providers in the library, the queue on Postgres

### Build
- **deploy:** dokploy template repacked with the capacity defaults

### CI
- **deploy:** a slim api image and a worker image with the toolchains, light and heavy workers, PgBouncer on a profile

### Chores
- merge master
- merge master

## v0.20.0 — 2026-09-18

### Features
- **web:** one DataTable for Activity, CI, Releases and Deployments, paged on the API
- **web:** one design for lists, forms and cards — Activity and CI as paginated lists with their own pages
- **web:** skeletons match the pages; Deployments lists the platform's runs only
- **web:** Releases and Deployments list only, paginated; New release and New deployment pages
- **api:** release as the platform's table — one row per tag, any source, referenced by deployments

### Refactoring
- releases and pull requests are read by the library's SourceHost providers
- **api:** ProjectService keeps to projects and apps; CI and deployments answer their own routes
- **api:** ReleaseStore lives in repositories — the releases and deployments contexts stay independent

### Chores
- merge master

## v0.19.0 — 2026-09-17

### Features
- **cli:** deployments and deploy-record against the hosted platform
- **web:** targets on the Deployments tab — live version per stage, deliveries by any executor, verified badge
- **api:** deployment records from the worker, observed pipelines and people; verified at the destination
- **deploy:** targets with an executor, and registries the platform verifies

### Bug Fixes
- **api:** ci_run.number as a big integer — GitHub Actions run ids overflow int32
- **api:** the GitHub App asks to read Actions, and the access check says when it cannot

### Docs
- **deployments:** targets and executors, the deployment record, verification at the destination

## v0.18.0 — 2026-09-17

### Features
- **api:** CI servers, the app's job and its imported runs
- **ci:** CIRunner reads runs; Jenkins and GitHub Actions providers

### Bug Fixes
- **api:** clone and fetch with the organization's credentials on GET routes

### Docs
- the CI tab, CI servers and the ci tables
- drop source file paths from user-facing guides
- **web:** shorter guide — no file paths, tables or routes; details linked
- the web app never reaches the database — diagrams and text corrected
- index.json listing the guides for the website
- web guide restructured one section per screen
- deployments concept, troubleshooting guide, richer glossary
- paths after the layered layout, getting started through deploy, no AP_PLUGINS_DIR
- the platform as it ships — deploy proxy flow, jobs and deploy sequence, contexts, aws/lambda for every web language, /health, one deploy per environment, cloud cleanup on delete
- **web:** one deploy per environment
- **web:** deleting a project with cloud cleanup
- **web:** releases and deletion dialogs
- **web:** deleting an app with cloud cleanup
- **web:** first deploy registers the app on the proxy; Target card rows
- **web:** Configure dialog
- **web:** the form on the plugin card
- **web:** Plugins page and Git on Settings
- **web:** Integrations as one page with the plugins

### Tests
- **api:** a deploy to a busy stage is refused; another stage is not
- **api:** project deletion with cloud cleanup
- **api:** deletion with cloud cleanup tears the stacks down on the worker, then removes the app
- **api:** the manages flag reaches the deploy token's scopes

### Build
- **deploy:** the API image carries Go 1.23, Node 22, JDK 21 + Maven and Ruby 3.3 — the worker builds every web language for aws/lambda
- **api:** apx-aws-lambda>=0.3.8 — aws/lambda for every web language
- **api:** lock apx-aws-lambda 0.3.7
- **api:** apx-aws-lambda>=0.3.7 — delete deregisters the app on the proxy
- **api:** apx-aws-lambda>=0.3.6 — the stack is named from the proxy's prefix
- **api:** apx-aws-lambda>=0.3.5 — the first deploy registers the app on the proxy
- **api:** apx-aws-lambda>=0.3.4 — the plugin declares its options

### Chores
- merge master
- merge master

## v0.17.9 — 2026-09-15

### Features
- **core:** a plugin declares its settings — Plugin.options (Option: key, label, kind, help, required) and a display name

### Bug Fixes
- **deploy:** drop the empty volumes keys left on api and worker — compose refuses a null list

### Docs
- **plugins:** declaring options
- **web:** Integrations → Git

### Tests
- **api:** plugin rows carry name and options

### Build
- **api:** python <3.14 (cfn-lint, aws-sam-cli caps) and cryptography>=50 — lock resolves aws-sam-cli 1.166.2
- **api:** bound python to <4.0 so poetry can solve aws-sam-cli; relock

### CI
- pin python 3.13 — aws-sam-cli and cfn-lint stop at <3.14

## v0.17.8 — 2026-09-15

### Breaking Changes
- **core:** drop AP_PLUGINS_DIR and AP_PLATFORM_ADMINS — plugins install into the interpreter's environment only

### Docs
- plugins are a dependency of the image; no runtime install, no platform admins, no plugins volume

### Tests
- **api:** plugins list the bundled ones and their load failures; install and restart routes are gone

### Build
- **deploy:** no plugins volume — the image carries its plugins

## v0.17.7 — 2026-09-15

### Features
- **web:** Organization (teams, members, sessions) and Integrations (code hosts, cloud) as their own sections; features/organization, integrations, account; old paths redirect

### Refactoring
- **web:** lib/api/<context>.ts — v1 assembled from organization, projects, integrations and jobs
- **web:** features/{projects,activity,releases,deployments,configuration} — pages stay in app/, code moves out; ESLint boundaries
- **api:** DirectoryService dissolved — OrganizationRepository, ProjectsRepository, IntegrationsDirectory, and the two compositions that span them (AccessDirectory, ImportDirectory)
- **api:** repositories by context — the directory's query mixins become repositories/{organization,projects,integrations}; workspace and configuration folders
- **api:** schemas and models named by context; routes import from the owning module
- **api:** services/integrations (hosts, plugins), services/organization (sessions), services/auth out of core
- **api:** services/projects (service, apps, organization_import) and services/templates
- **api:** services by context — activity, releases, deployments, configuration
- **api:** routers become api/routes — one file per context, deployments apart from releases

### Docs
- **agents:** new code goes in the context folder of each layer
- the contexts of the API and the web app, one folder per layer, and the rule for new code
- **architecture:** api/routes

### Tests
- **api:** worker import path; docs

### CI
- contracts for the layout by context — routes → services → repositories → schemas → core; independent app contexts; git_auth leaves core

### Style
- **api:** format

## v0.17.6 — 2026-09-15

### Features
- **api:** migrations move to the deploy — AP_DATABASE_AUTO_MIGRATE, advisory lock, readiness on /api/version
- **api:** platform admins (AP_PLATFORM_ADMINS) — the role that changes the platform itself

### Refactoring
- **core:** the core reaches plugins through the Extensions port; the package's composition root wires the registry
- **api:** the CLI entry points move out of core — core imports no services

### Docs
- **architecture:** the extensions port
- **architecture:** the layer rule is enforced
- **architecture:** directory and catalog modules
- **architecture:** cli, plugins catalog
- **architecture:** access collaborators
- **architecture:** worker pieces
- **architecture:** commit service
- **architecture:** registry rows vs workspaces
- **architecture:** the layer rule for errors
- **self-hosting:** migrations on deploy
- **web:** host imports run on the worker
- **self-hosting:** AP_PLATFORM_ADMINS
- platform admins and per-organization plugin options

### Tests
- **api:** deploy env and job context through their public objects
- **api:** adopting a repository goes through Workspaces
- **api:** readiness reflects pending migrations
- **api:** oversized body is refused
- **api:** an inline call with imports queues the import job
- **api:** plugin option scoping and platform admin gate

### Build
- **deploy:** one-shot migrate service the API and the worker wait for

### CI
- web tests in the quality workflow
- core may not import plugins
- run import-linter through the interpreter poetry resolved
- import-linter contracts for the layers
- run quality, commits and scan on pull requests to develop; manual api publish reads apps/api/app/LAST_VERSION

### Chores
- **deps:** lock import-linter
- merge master
- merge master
- merge master
- merge master
- merge master
- merge master

## v0.17.5 — 2026-09-15

### Features
- **core:** Config.from_dict and dump_toml — the tables of platform.toml from and to any store

### Docs
- configuration kept by the platform, platform.toml as its mirror

### Tests
- configuration kept by the platform, exported on request

## v0.17.4 — 2026-09-15

### Features
- **core:** a release takes a name, Markdown notes above the commit list, and whether it is the latest
- **cli:** --version on deploy; version on the MCP deploy tools
- **core:** a deploy ships a release — names a version or takes the tag at HEAD, checks it out, refuses anything else
- **core:** ActionPlatform and Deployer take env the platform fills into ctx.env for targets

### Docs
- Releases tab and release fields
- **web:** Deployments tab
- deploys ship releases
- **web:** AWS integration

### Tests
- **core:** deploys ship releases
- **api:** deploy env from options

### Build
- **api:** make in the image for SAM makefile builds

### Chores
- merge master
- **api:** apx-aws-lambda 0.3.3

## v0.17.3 — 2026-09-15

### Features
- **api:** bundle apx-aws-lambda in the API image

### Bug Fixes
- **scaffold:** overlays render with the project's name as project_slug, not the workspace directory

### Docs
- **web:** overview and Deployments tab
- **plugins:** the hosted platform bundles aws-lambda; no marketplace in the web
- **web:** the Deploy card
- **identity:** scopes claim

### Tests
- **api:** deploy jobs listing
- **api:** switching an unknown plugin, now that aws-lambda is bundled
- **api:** identity token scopes

## v0.17.2 — 2026-09-15

### Bug Fixes
- **plugins:** a removed plugin stays disabled until the restart forgets it, and cannot be enabled meanwhile

### Tests
- **plugins:** removal flow through disable, restart and discovery

## v0.17.1 — 2026-09-15

### Bug Fixes
- **plugins:** a plugin loads on an install without the mcp extra — action_platform.mcp imports without the SDK; a load failure names its cause

### Build
- **deploy:** plugins volume in every compose; build.sh keeps docker-compose.dokploy.yml in step with the template

## v0.17.0 — 2026-09-15

### Features
- **remote:** identity_token
- **api:** the platform as an OIDC issuer — discovery, JWKS, tokens per deploy from the worker and for logged-in callers
- **core:** a deploy context can ask for an identity token; ActionPlatform and Deployer carry the signer
- **plugins:** AP_PLUGINS_DIR as a shared install directory, refresh when plugins.json changes, options store on the surface, pip installer shared by CLI and platform

### Docs
- identity — deploys without cloud access keys
- hosted plugins, options store

### Tests
- plugin options, refresh, hosted install and options endpoints

### Build
- **deploy:** plugins volume for the api and the worker

## v0.16.1 — 2026-09-15

### Features
- **api:** GET /api/plugins — the plugins index plus which plugins this platform runs

### Docs
- plugins marketplace

### Tests
- **mcp:** skip the mcp surface tests when the extra is not installed

## v0.16.0 — 2026-09-15

### Features
- **core:** slots import their home lazily; plain overlays without cookiecutter are copied as they are
- **abc:** export Surface
- **hooks:** git hooks ask action-platform gitflow-check when the CLI is on PATH, so replaced rules hold at commit time
- **plugins:** Plugin ABC, discovery through action_platform.plugins, on/off state, tools as <slug>.<name>, overlays, lifecycle hooks, action-platform plugin commands
- **release:** [release] strategy and changelog pick a ReleaseStrategy / ChangelogRenderer — semver and conventional built in, others from entry points
- **core:** every process is a class in a wiring slot — gitflow_rules, gitflow, releaser, deployer, installer, scaffolder — so a plugin can replace it with a subclass

### Refactoring
- **plugins:** packages are apx-<slug>; tools come out as <slug>_<name> since MCP clients refuse dots

### Docs
- plain overlays
- plugins — using, writing, wiring slots and providers

### Tests
- **mcp:** the core surface ignores plugin tools
- **plugins:** plain overlay
- plugins registry, wiring slots, release strategies; hooks call gitflow-check

### CI
- plugin issue template

## v0.15.0 — 2026-09-15

### Features
- **mcp:** ci none on install_platform and install_ci; cli help says so
- **install:** ci none writes no pipeline files; git-flow stays enforced by the hooks

### Docs
- --ci none

### Tests
- **install:** ci none

## v0.14.0 — 2026-09-15

### Features
- **mcp:** prompts on the remote server — orient, new_app, ship_change, cut_release, deploy_app, adopt_repository
- **remote:** project-scoped app endpoints and X-Organization on directory calls
- **mcp:** output schemas on every tool; remote add_app/init_app take a project, remove_app and delete_project can drop repositories
- **mcp:** tools register through one decorator that turns platform errors into readable tool errors; both servers state the rules

### Bug Fixes
- **deploy:** web image installs with npm install; the lock written on macOS misses linux-only optional packages

### Docs
- remote prompts
- remote apps live in projects; the rules both MCP servers state
- settings pages and sidebar after the navigation change

### Tests
- **mcp:** both servers offer prompts
- **mcp:** remote tools against project rows, readable errors, every tool has schemas and rules

### Style
- format tests/core/test_env.py

### Chores
- skills and plugin manifests move to actionplatform/action-platform-mcp

## v0.13.0 — 2026-09-14

### Features
- **env:** a .env in the working directory fills in unset variables for the CLI, the API and the worker; api errors print one line
- **web:** settings split into pages — General, Members, Code hosts, Git-flow, API — as a sidebar submenu and tabs on a phone

### Refactoring
- **api:** TokenMinter, ImportGateway and HostConnector.create_github_app take the last orchestration out of the routers; import schemas in schemas/imports
- **api:** routes only translate HTTP — ProjectService (add, init, delete, sync activity) and HostConnector (OAuth finish) hold the orchestration
- **api:** routes declare their dependencies as Annotated types (CallerDep, OrgDep, WritesDep, …)
- **api:** routers and schemas by domain — auth, organizations, hosts, projects, apps, catalog, jobs
- **api:** routers by context (workspace, management, auth packages) over api/dependencies; AuthService and the models split by context; delete_through_host on AppRemote
- **api:** core never imports services (caller and enrich live in services/access), core/auth is a real package, one ruff config for the whole repository

### CI
- **web:** npm install, the lock written on macOS misses linux-only optional packages for npm ci

## v0.12.0 — 2026-09-14

### Refactoring
- **api:** the package is app
- the API is its own package under apps/api (action_platform_api): core (abc, access, auth, db, cli, shared), api (FastAPI), repositories, services, schemas; the library no longer ships api extras or api commands; action-platform-api serve|worker|db; shared test fixtures in action_platform.testing
- **api:** contracts only the API implements live in api/abc

### Build
- **api:** standard layout apps/api/action_platform_api with poetry packaging
- regenerate poetry.lock without the api extras

### CI
- install the API's dev extra
- resolve the interpreter before entering apps/api
- run the API tests with the root environment

## v0.11.1 — 2026-09-14

### Features
- **release:** a repository without a version tag is at 0.0.0 whatever LAST_VERSION says

### Refactoring
- **api:** services as structured classes — HostProvider per code host (OAuth, refresh, access), import steps as classes, MatrixView, TemplateRepos, AppManifest, GitUrl, HttpClient, Clones; every __init__ only re-exports
- **abc:** Vcs becomes WorkingCopy
- **api:** every service in a package — workspace, catalog, jobs, shared; ImportSource and HostDirectory ABCs behind imports and github_import
- **api:** services split into packages — directory (one module per domain), hosts (oauth and providers), imports (per provider), apps (inventory, generate, remote); common and credentials helpers

### Docs
- **import:** projects

### Tests
- **release:** untagged repository starts at zero
- **import:** github project into an existing project
- **import:** projects and a target project

## v0.11.0 — 2026-09-14

### Features
- **api:** nothing local survives: init pushes at once, commits and branches push, checkout is a registry field, edits are drafts
- **db:** checked-out branch per app and pending edits (draft table); workspaces under the temp dir

### Bug Fixes
- **db:** pool of 10 with 20 overflow by default, both configurable

### Docs
- **api:** sync semantics
- stateless api and worker; no apdata volume
- **import:** members permission
- **db:** pool settings

### Tests
- **api:** stateless workspaces, drafts and pushes into the fixture
- **import:** organizations answer shape

## v0.10.2 — 2026-09-14

### Docs
- **web:** import

### Tests
- **api:** github import preview, permissions and job

## v0.10.1 — 2026-09-14

### Features
- **providers:** delete_repository on github, gitlab and bitbucket

### Docs
- **web:** deleting apps and repositories

### Tests
- **api:** repository deletion needs an attached host and reports what it removed

### Style
- **cli:** format install help

## v0.10.0 — 2026-09-14

### Features
- **catalog:** revalidate the templates index with its ETag every minute instead of caching it ten
- **scaffold:** detect ruby by Gemfile or .rb and sync VERSION in version.rb on release

### Docs
- **templates:** index revalidation
- list every web stack, ruby included

### Tests
- **catalog:** etag revalidation keeps the cache on 304
- **scaffold:** ruby detection and version.rb sync

## v0.9.0 — 2026-09-14

### Features
- **login:** asks for every scope and every organization by default; the device page lists all scopes as checkboxes, pre-selected and locked by the role; --scope narrows

## v0.8.0 — 2026-09-14

### Features
- **core:** the catalog is index.json — Matrix.from_json/from_dict with types, stacks, frameworks and icons; templates ref defaults to main

### Docs
- index.json, raw catalog and the templates ref

### Tests
- index.json fixtures; catalog from the published index and its fallback

## v0.7.1 — 2026-09-14

### Features
- **core:** access catalog with labels and descriptions; Releaser.next_version and GitFlow.plan_branch previews

### Docs
- previews and the access catalog
- registry without a file fallback
- registry adoption

### Tests
- **api:** access catalog, next-version and branch plan previews
- **api:** registry on the database everywhere; adoption renames apps.json
- **api:** registry adopts apps.json
- **api:** dead OAuth token on host access

### Style
- **test:** ruff format

## v0.7.0 — 2026-09-13

### Features
- **cli:** action-platform worker
- **api:** directory, credentials and imports in Python — projects, apps, teams, members, source-host tokens decrypted (and refreshed) from the web app's ciphertext, commit identity, template sources, releases and pull requests copied from the host
- **api:** auth owned by the API — sign-up/sign-in with better-auth-compatible scrypt hashes and signed cookies, sessions, organizations and members, RFC 8628 device flow, scoped JWT tokens, per-IP rate limits
- **core:** access rules in Python — roles, permissions, scopes, grantable scopes and Grant

### Docs
- the web app is a client; management routes; what the database holds; setup wizard
- registry in the database, jobs and the worker, async calls
- the /api/v1 gate, what the API fills in, what still lives in the web app
- auth endpoints, access rules in Python, setup wizard and self-hosting variables

### Tests
- **api:** management routes — projects and apps, teams, members and invitations, hosts, OAuth apps and flows, settings, template sources
- **api:** queue claim/finish/retry/reap, async route to worker, job visibility, workspace rebuilt
- **api:** the gate — identity, directory, management, reach, credentials, ciphertext, template sources
- **api:** accounts, cookies, device flow, tokens, members, rate limits

### Build
- **api:** cryptography for the source-host ciphertext
- sentry-sdk in the dev group too
- fastapi, sqlalchemy and alembic in the dev group so CI runs the API tests

### Style
- **api:** blank lines between the steps inside functions
- **core:** ruff format

### Chores
- **deploy:** web container without database, secret or config volume; image without drizzle
- **deploy:** worker service on the API image, sharing apdata
- **deploy:** API receives the OAuth app credentials to refresh host tokens
- **deploy:** API receives AP_AUTH_SECRET and AP_PUBLIC_URL

## v0.6.13 — 2026-09-13

### Features
- **cli:** db status and db migrate
- **api:** own the database — SQLAlchemy models for every web table plus job, Alembic migrations run on boot, an existing web schema is adopted, AP_DATABASE_URL and get_db

### Bug Fixes
- **core:** match remote tags and branches by full ref, so web/v0.6.13 no longer shadows v0.6.13
- **web:** open redirect closed, security headers, HKDF subkeys and audience on tokens, OAuth state bound to the user, timeouts on every outbound call, rate limits, explicit read rules, filtered queries, pool size via env
- **api:** refuse to start without AP_API_TOKEN unless AP_ALLOW_UNAUTHENTICATED=1; tighter CORS; proxy headers; credentials file created 0600; bearer tokens redacted from remote errors

### Docs
- database concept guide, db commands, self-hosting variables; stray conflict markers removed

### Tests
- **api:** migrations from empty and from a web-created schema, sessions, job dedupe, boot wiring

### Build
- **api:** sqlalchemy, alembic, psycopg and pymysql in the api extra

### Chores
- **deploy:** API gets AP_DATABASE_URL and waits for Postgres in every compose file

## v0.6.12 — 2026-09-13

### Features
- Bitbucket Pipelines as a CI provider — install, wizard, import, auto-heal default to it for Bitbucket remotes

## v0.6.11 — 2026-09-13

### Bug Fixes
- **providers:** Bitbucket sends an OAuth access token as Bearer instead of Basic with the git pseudo-user

## v0.6.10 — 2026-09-13

### Features
- **core:** install picks GitLab CI for a GitLab remote when no CI is chosen

### Docs
- **readme:** documentation map by context, scoped tokens and connected apps, versions and changelogs
- index links changelogs, versions, contributing, code of conduct, security and license
- index leads with what the reader wants to do; conventions and glossary
- one file per context and topic (start, use, concept, contribute); real routes, tools, flags and tables; access control, API and getting started guides

## v0.6.9 — 2026-09-13

### Features
- **mcp:** report the MCP client's name to the platform; organization argument on organization-level tools

### Bug Fixes
- **cli:** login and whoami name the project and app the token is limited to
- **api:** a fetch the code host refuses fails the sync with a reason instead of a 500

### Docs
- device approval, all-organization tokens, connected apps

## v0.6.8 — 2026-09-13

### Features
- **mcp:** whoami with role, scope and permissions; current_context; organization, project, team and member tools including management

### Docs
- token reach, connected apps, MCP orientation and management tools

## v0.6.7 — 2026-09-13

### Features
- **cli:** login polls on the OAuth error code and mints a scoped bearer token (--scope, --name)

### Bug Fixes
- **core:** fall back to tracking refs when the remote cannot be asked without credentials

### Refactoring
- **api:** services, CLI and MCP tools call Repository, GitFlow, Installer and Manifest
- module-level imports everywhere the dependency graph allows
- **core:** TemplateStore, LanguageDetector and Installer (plan/apply) split out of templates.py and install.py
- **core:** Manifest object over platform.toml
- **core:** Version, VersionFiles, Releaser (plan → apply) and Deployer behind the ActionPlatform facade
- **core:** GitFlow(repo) replaces branching, pullrequest and the audit/hooks functions; gitflow.py is the rules only
- **core:** Repository — every git command on one clone, follow_remote and stashed included; git.py keeps only the policies

### Docs
- the objects in the core
- token scopes, API tokens card and mobile layout

## v0.6.6 — 2026-09-13

### Features
- **api:** sync moves a branch with leftover local commits to its remote, keeping uncommitted work
- **api:** put the platform files back whenever a clone is opened without platform.toml

### Bug Fixes
- **api:** configuration commits are made with the identity sent in the request, not only the push
- **api:** one SourceCredentials model where the token and the commit identity are each optional

### Docs
- commit identity travels with every request
- self-healing clones, automatic sync reset and the pull request banner

## v0.6.5 — 2026-09-13

### Features
- **api:** report the api component version in /api/version and Sentry; sidebar shows web, api and lib versions
- **api:** sync leaves merged branches, follows rewritten remotes and accepts reset=true to match the remote

### Bug Fixes
- **core:** fast-forward before a release and roll the commit and tag back when the push is refused

### Docs
- sync reset, release rollback and Sentry capture of action failures

### Chores
- strip comments from the generated API client and the git hooks

## v0.6.4 — 2026-09-13

### Features
- **api:** optional Sentry reporting for the API and the CLI via AP_SENTRY_DSN
- **web:** commit identity per organization, set in setup and settings, sent with every platform commit

### Bug Fixes
- **core:** audit protected branches from the platform install commit and stop flagging merged pull requests as direct commits
- **api:** sync stashes local changes around the pull instead of refusing
- **api:** answer 400 instead of 500 when a clone has no platform.toml, and add POST /apps/{id}/install to write it again
- **web:** server actions never throw past their boundary; request errors are logged as JSON; platform git email cloud@actionplatform.io
- **api:** commits on the platform are authored by the signed-in user, with a platform default identity
- list and discard uncommitted changes in the workspace, undo release writes when the commit fails, show the sync error
- **providers:** check credentials when a call is made, not when platform.toml is read — the API applies the request token after loading the config
- **web:** apps without a remembered host pick the organization's matching host before push, release and pull request
- **web:** create the GitHub App as public so it can be installed on any organization; say so when GitHub skips the account picker

### Docs
- observability guide, Sentry variables in the compose files and the reinstall flow
- **readme:** keep only the cli, web and api version badges

## v0.6.3 — 2026-09-13

### Features
- **web:** namespace choice for GitLab groups and Bitbucket workspaces when creating an app, with the same access check as GitHub

### Bug Fixes
- **gitlab:** authenticate API calls with Authorization: Bearer so OAuth tokens work, not only personal access tokens
- **web:** pick the GitHub organization from the app's installations when creating an app

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
