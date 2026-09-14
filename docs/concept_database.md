# Database

One Postgres (or MySQL, or SQLite) holds every organization, project, app, token and session. Today the web app created it and owns most writes; the Python API now connects to the same database, runs its own migrations and keeps the schema — the first step of moving every business rule into the API (see [architecture](contribute_architecture.md)).

## Connecting the API

| Variable | Meaning |
|---|---|
| `AP_DATABASE_URL` (or `DATABASE_URL`) | `postgres://user:pass@host/db`, `mysql://…` or `sqlite:///path.db`. Empty keeps the API database-less; routes that need one answer `503 no database configured`. |
| `AP_DATABASE_POOL_SIZE` | connections per API process (default 5; SQLite ignores it) |

`postgres://` and `postgresql://` are rewritten to the `psycopg` driver, `mysql://` to `pymysql`; both ship with `pip install 'action-platform[api]'`.

On boot the API migrates to the latest revision before it serves a request. The compose files point `AP_DATABASE_URL` at the same Postgres as the web app and start the API only after Postgres is healthy.

## Migrations

Alembic, under `action_platform/api/db/migrations/versions/`:

| Revision | What |
|---|---|
| `0001` | the 19 tables the web app already has — same names, same columns, same foreign keys and cascades |
| `0002` | `job`: the queue for clone, sync, release and deploy work |

A database the web app created has no `alembic_version` table but does have `user`; the API recognises that, stamps it at `0001` and applies only what follows. Nothing is recreated, nothing is copied: pointing the API at the web app's database is the whole data migration.

```bash
action-platform db status                       # dialect, current and head revision
action-platform db migrate                      # same as boot, on demand
action-platform db migrate --url sqlite:///dev.db
```

Both read `AP_DATABASE_URL` unless `--url` is given.

## Tables

`user`, `session`, `account`, `verification`, `device_code` — accounts and sign-ins. `organization`, `member`, `invitation`, `team`, `team_member` — who belongs where. `project`, `app`, `source_host`, `template_source`, `organization_setting` — what each organization runs. `release`, `pull_request` — imported from the source host. `api_token`, `api_token_client` — tokens from `action-platform login` and the clients seen using them. `job` — queued work with `kind`, `status` (`queued` → `running` → `done` | `failed`), `attempts`, `run_after`, `locked_at` / `locked_by` and a `dedupe_key` unique per app and kind so the same sync is never queued twice.

Models live in `action_platform/api/db/models.py` (SQLAlchemy 2, one class per table, parents reachable from children); `Database` in `database.py` owns the engine, `migrate()` and a `session()` context manager that commits on success and rolls back on any exception. Ids are 36-character strings, so the same rows are valid on every dialect and the ids the web app minted stay as they are.

## What still lives in the web app

Authentication (better-auth), the OAuth flows with GitHub, GitLab and Bitbucket, token issuing and the permission checks in `/api/v1` — each moves to the API in the following steps; the web app keeps its drizzle migrations until then and both sides share the schema at revision `0001`.
