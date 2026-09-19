# Database

One Postgres (or MySQL, or SQLite) holds every organization, project, app, token and session. Today the web app created it and owns most writes; the Python API now connects to the same database, runs its own migrations and keeps the schema — the first step of moving every business rule into the API (see [architecture](contribute_architecture.md)).

## Connecting the API

| Variable | Meaning |
|---|---|
| `AP_DATABASE_URL` (or `DATABASE_URL`) | `postgres://user:pass@host/db`, `mysql://…` or `sqlite:///path.db`. Required: the API refuses to start without it. |
| `AP_DATABASE_POOL_SIZE` | connections kept open per API process (default 10; SQLite ignores it) |
| `AP_DATABASE_MAX_OVERFLOW` | extra connections opened under load and closed afterwards (default 20) |

Postgres and MySQL drivers ship with the API; SQLite needs nothing.

On boot the API migrates to the latest revision before it serves a request. The compose files start the API and the worker only after Postgres is healthy.

## Migrations

Alembic, shipped with the API — one revision per change:

| Revision | What |
|---|---|
| `0001` | the 19 tables the web app already has — same names, same columns, same foreign keys and cascades |
| `0002` | `job`: the queue for sync, release, deploy, push, import and tear-down (`destroy`, `destroy_project`) work |
| `0003` | `registry`: the apps the API manages (id, name, url, default branch), shared by every instance and worker |
| `0004` | `oauth_app`: the OAuth apps used to connect code hosts (client id, sealed secret, base URL, GitHub App slug) |
| `0005` | `registry.branch` and `draft`: the checked-out branch per app and pending edits as rows — clones are disposable |
| `0006`, `0009` | `plugin_option`: what a plugin remembers, keyed by organization, plugin and key (the values behind Plugins → Configure) |
| `0007` | `signing_key`: the RSA pair behind the platform's OIDC issuer, private half sealed |
| `0008` | `app_config`: the app's `platform.toml` as the platform keeps it — the database is the source of truth, the file in the repository a mirror |
| `0010`, `0011` | `ci_host`, `ci_run`, `app.ci_host_id` and `app.ci_job`: the CI servers an organization connected (token sealed), the runner and job each app reads, and the runs imported from it (`number` a big integer: GitHub run ids) |
| `0012` | `deployment`: a release arriving at one of the app's targets — target, stage, version, status up to `verified`, executor (platform, GitHub Actions, Jenkins, manual), the job or CI run that did it |
| `0013` | `release` becomes the platform's table: `component` and `version` per tag, one row per `(app, tag)`, `source` naming who first knew it (`platform`, a host, `git`); `deployment.release_id` references it |
| `0014` | indexes on every per-app listing (`release`, `pull_request`, `ci_run`, `deployment`, `job`) and on the queue's claim, hosts and members by organization |
| `0015` | `app_snapshot`: what the app pages read, one JSON row per app, taken from the clone after every change — reads never touch git |
| `0016` | `source_host.webhook_secret_encrypted`: the secret the host signs deliveries with |
| `0017` | `release_readiness`: whether a release can reach a stage — one row per `(release, stage)` with `status`, `ok`, the checks as JSON, the job that ran them and when |
| `0018` | `job_log`: every line a job wrote, in order (`job_id`, `seq`, `line`, `at`), appended by the worker as it runs so a page can follow |
| `0019` | `scope`: where an app's releases are deployed — name, kind, criticality; `release.shape`: candidate, stable or hotfix |
| `0020` | `scope` loses the columns an earlier build wrote (target, options, run_by, url, derived) and `app.scopes_seeded` |

A database the web app created has no `alembic_version` table but does have `user`; the API recognises that, stamps it at `0001` and applies only what follows. Nothing is recreated, nothing is copied: pointing the API at the web app's database is the whole data migration.

```bash
action-platform-api db status                       # dialect, current and head revision
action-platform-api db migrate                      # same as boot, on demand
action-platform-api db migrate --url sqlite:///dev.db
```

Both read `AP_DATABASE_URL` unless `--url` is given.

## Tables

`user`, `session`, `account`, `verification`, `device_code` — accounts and sign-ins. `organization`, `member`, `invitation`, `team`, `team_member` — who belongs where. `project`, `app`, `source_host`, `template_source`, `organization_setting` — what each organization runs. `release`, `pull_request` — the platform's releases (any source) and pull requests imported from the source host; `release_readiness` — per release and stage, whether it can be deployed there, as the worker last checked. `api_token`, `api_token_client` — tokens from `action-platform login` and the clients seen using them. `registry` — the apps the API manages. `job_log` — what each job wrote, one row per line. `job` — queued work with `kind`, `status` (`queued` → `running` → `done` | `failed`), `attempts`, `run_after`, `locked_at` / `locked_by` and a `dedupe_key` unique per app and kind so the same sync is never queued twice.

## Jobs

The queue claims with `SELECT … FOR UPDATE SKIP LOCKED` on Postgres and a compare-and-set update elsewhere, so several workers share one queue without taking the same row. `action-platform-api worker [--once] [--interval]` loops: reap jobs whose worker vanished (running for over thirty minutes), claim, run, `done` with the result or `failed` with the error — a refusal from the platform's own rules fails at once, anything else retries up to three times with a 30 s · 2ⁿ backoff. Payloads never hold credentials; the worker reads them from `source_host` when it runs, exactly as the gate does for inline calls ([API](use_api.md#jobs)).

One model per table, grouped by context (auth, organization, projects, configuration, activity, integrations, jobs); every request runs in one session that commits on success and rolls back on any exception. Ids are 36-character strings, valid on every dialect.

## What still lives in the web app

Nothing. The web app has no database connection, no secret and no migrations: it reads and writes through `/api/v1` and `/api/auth` with the caller's cookie. Every rule — who may do what, which token opens which repository, what a device may be granted — is Python.
