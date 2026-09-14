# Database

One Postgres (or MySQL, or SQLite) holds every organization, project, app, token and session. Today the web app created it and owns most writes; the Python API now connects to the same database, runs its own migrations and keeps the schema — the first step of moving every business rule into the API (see [architecture](contribute_architecture.md)).

## Connecting the API

| Variable | Meaning |
|---|---|
| `AP_DATABASE_URL` (or `DATABASE_URL`) | `postgres://user:pass@host/db`, `mysql://…` or `sqlite:///path.db`. Required: the API refuses to start without it. |
| `AP_DATABASE_POOL_SIZE` | connections kept open per API process (default 10; SQLite ignores it) |
| `AP_DATABASE_MAX_OVERFLOW` | extra connections opened under load and closed afterwards (default 20) |

`postgres://` and `postgresql://` are rewritten to the `psycopg` driver, `mysql://` to `pymysql`; both ship with `pip install 'action-platform[api]'`.

On boot the API migrates to the latest revision before it serves a request. The compose files point `AP_DATABASE_URL` at the same Postgres as the web app and start the API only after Postgres is healthy.

## Migrations

Alembic, under `action_platform/api/db/migrations/versions/`:

| Revision | What |
|---|---|
| `0001` | the 19 tables the web app already has — same names, same columns, same foreign keys and cascades |
| `0002` | `job`: the queue for sync, release, deploy, push and import work |
| `0003` | `registry`: the apps the API manages (id, name, url, default branch), shared by every instance and worker |
| `0004` | `oauth_app`: the OAuth apps used to connect code hosts (client id, sealed secret, base URL, GitHub App slug) |

A database the web app created has no `alembic_version` table but does have `user`; the API recognises that, stamps it at `0001` and applies only what follows. Nothing is recreated, nothing is copied: pointing the API at the web app's database is the whole data migration.

```bash
action-platform db status                       # dialect, current and head revision
action-platform db migrate                      # same as boot, on demand
action-platform db migrate --url sqlite:///dev.db
```

Both read `AP_DATABASE_URL` unless `--url` is given.

## Tables

`user`, `session`, `account`, `verification`, `device_code` — accounts and sign-ins. `organization`, `member`, `invitation`, `team`, `team_member` — who belongs where. `project`, `app`, `source_host`, `template_source`, `organization_setting` — what each organization runs. `release`, `pull_request` — imported from the source host. `api_token`, `api_token_client` — tokens from `action-platform login` and the clients seen using them. `registry` — the apps the API manages. `job` — queued work with `kind`, `status` (`queued` → `running` → `done` | `failed`), `attempts`, `run_after`, `locked_at` / `locked_by` and a `dedupe_key` unique per app and kind so the same sync is never queued twice.

## Jobs

`JobQueue` (`action_platform/api/services/jobs.py`) claims with `SELECT … FOR UPDATE SKIP LOCKED` on Postgres and a compare-and-set update elsewhere, so several workers share one queue without taking the same row. `action-platform worker [--once] [--interval]` loops: reap jobs whose worker vanished (running for over thirty minutes), claim, run, `done` with the result or `failed` with the error — a refusal from the platform's own rules (`ActionPlatformError`) fails at once, anything else retries up to three times with a 30 s · 2ⁿ backoff. Payloads never hold credentials; the worker reads them from `source_host` when it runs, exactly as the gate does for inline calls ([API](use_api.md#jobs)).

Models live in `action_platform/api/db/models.py` (SQLAlchemy 2, one class per table, parents reachable from children); `Database` in `database.py` owns the engine, `migrate()` and a `session()` context manager that commits on success and rolls back on any exception. Ids are 36-character strings, so the same rows are valid on every dialect and the ids the web app minted stay as they are.

## What still lives in the web app

Nothing. The web app has no database connection, no secret and no migrations: it reads and writes through `/api/v1` and `/api/auth` with the caller's cookie. Every rule — who may do what, which token opens which repository, what a device may be granted — is Python.
