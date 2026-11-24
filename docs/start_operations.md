# Operations

Backups, restores and secret rotation for a self-hosted platform. Commands run in the install directory (`/opt/action-platform` with `install.sh`); add `--profile tls` to `docker compose up` when the instance has a domain. On Dokploy the services are prefixed (`ap-postgres`, `ap-api`, …) and the commands run on the host with `docker exec` against their containers (`docker ps --filter name=ap-postgres`).

## What holds state

| What | Where | Lost means |
|---|---|---|
| The database | volume `pgdata` (service `postgres`) | everything: accounts, organizations, projects, apps, releases, deployments, jobs, sealed tokens, plugin options |
| `BETTER_AUTH_SECRET` | `secrets/better_auth_secret`; on Dokploy `BETTER_AUTH_SECRET` under *Environment* | every sealed value in the database becomes unreadable — see [losing the auth secret](#losing-the-auth-secret) |
| Postgres password | `secrets/postgres_password`; Dokploy `POSTGRES_PASSWORD` | nothing: it can be set again (see [rotation](#the-postgres-password)) |
| `AP_API_TOKEN` | `secrets/api_token`; Dokploy `AP_API_TOKEN` | nothing: any new value works |
| Settings | `.env`; Dokploy *Environment* | `PUBLIC_URL`, OAuth, SMTP and Google settings to type again |

Clones, build artifacts and the containers themselves are rebuilt from the code hosts and the images. A backup is the database dump plus `secrets/better_auth_secret` (and `.env`), kept together and off the host.

## Backup

**One dump, now**:

```bash
mkdir -p backups
docker compose exec -T postgres pg_dump -U action_platform action_platform > backups/action_platform-$(date -u +%Y%m%dT%H%M%SZ).sql
```

On Dokploy: `docker exec $(docker ps -qf name=ap-postgres) pg_dump -U action_platform action_platform > action_platform.sql`.

**Every day**: the `backup` service dumps with `pg_dump`, gzips into `action_platform-<UTC time>.sql.gz`, once when it starts and then every day at `AP_BACKUP_HOUR` (UTC, 0-23, default 3), and deletes the dumps older than `AP_BACKUP_KEEP_DAYS` days (default 7). A failed dump leaves no file and logs `backup failed`.

- Compose: opt in with `docker compose --profile backup up -d backup`. Dumps land in `./backups` on the host (`AP_BACKUP_DIR` moves them), next to the `pre-upgrade-*.sql` files `install.sh` writes before an upgrade (the retention never deletes those).
- Dokploy: the template runs it as `ap-backup`, writing into the `backups` volume of the stack; set `AP_BACKUP_HOUR` and `AP_BACKUP_KEEP_DAYS` under *Environment*. Dokploy's **Volume Backups** can copy that volume (or `pgdata`) to S3 on a schedule.

`docker compose logs backup` shows each `wrote …` line. Copy the dumps and the secret off the host; a backup on the same disk dies with it.

**`action-platform-api db backup`** does the same from the api or worker image, for a database outside the compose stack (a managed Postgres): `--out FILE` (default `action_platform-<UTC time>.sql` in the working directory), `--out -` for stdout; it reads `AP_DATABASE_URL` (or `--url`). From the compose stack:

```bash
docker compose exec -T api action-platform-api db backup --out - > backups/action_platform.sql
```

## Restore into a fresh host

1. Install as usual (`install.sh` with the same arguments, or import the template on Dokploy), with the same versions as the backup: `AP_REF=api/vX.Y.Z AP_WEB_REF=web/vX.Y.Z` (the versions `GET /api/version` reported, or the tags in the old `.env`).
2. Put the old secret back before anything signs in: copy `better_auth_secret` into `secrets/` (Dokploy: paste it as `BETTER_AUTH_SECRET`). Copy `.env` settings you need (`PUBLIC_URL`, OAuth, SMTP, Google).
3. Stop everything that talks to the database, keep Postgres:

   ```bash
   docker compose stop web worker worker-deploy api
   ```

4. Recreate the database and load the dump (`gunzip -c file.sql.gz |` in front for a daily dump):

   ```bash
   docker compose exec -T postgres psql -U action_platform -d postgres \
     -c 'DROP DATABASE action_platform' -c 'CREATE DATABASE action_platform OWNER action_platform'
   docker compose exec -T postgres psql -U action_platform -v ON_ERROR_STOP=1 --single-transaction action_platform < backups/action_platform.sql
   ```

   Or, through the api image: `docker compose run --rm --no-deps -T api action-platform-api db restore - --force < backups/action_platform.sql`. `db restore FILE` (or `-` for stdin) loads a plain SQL dump with `psql` in one transaction and refuses a database that already has tables unless `--force`, which drops them in that same transaction.

5. Start again; the `migrate` service brings the schema up to the image before `api` and the workers start:

   ```bash
   docker compose up -d
   ```

On Dokploy: stop `ap-web`, `ap-worker`, `ap-worker-deploy` and `ap-api` with `docker stop`, run step 4 with `docker exec -i $(docker ps -qf name=ap-postgres)` in place of `docker compose exec -T postgres`, then **Deploy**.

### Check the restore

- `GET /api/version` (or the sidebar footer) shows the versions and `ready: true`.
- Sign in with an existing account; the organizations, projects and apps are there.
- Settings → **Git**: a connected host lists its account; an app's **Sync** succeeds (the stored token opens).
- Settings → **CI servers**: *Test* reaches the server.
- **Plugins** → a plugin → **Configure** opens with its saved options.

If those last three fail with a decryption error, the secret is not the one the backup was taken with: go back to step 2, or follow [losing the auth secret](#losing-the-auth-secret).

## Losing the auth secret

`BETTER_AUTH_SECRET` (`AP_AUTH_SECRET` inside the API) signs and seals; nothing else does. With another value:

| Sealed or signed with it | What happens | Recovery |
|---|---|---|
| Browser sessions | signed out | sign in again; passwords are hashed without the secret and keep working |
| CLI and MCP tokens (`action-platform login`) | `401` | `action-platform login <url>` again; the old tokens can be revoked under **Sessions** (the key icon next to your name) |
| Source host tokens, refresh tokens and webhook secrets | sync, push, release and import fail | Settings → **Git**: *Remove host*, then **Connect with …** again; generate the *Webhook…* secret again and paste it on the host |
| Service connections (Settings → **Services**, e.g. Sentry) | the plugins that read them fail | *Connect* the service again under Settings → **Services** |
| CI server tokens (Jenkins) | *Test* and dispatched deploys fail | Settings → **CI servers**: remove the server and add it again with its API token |
| OAuth apps stored in the database (*Set up OAuth app*, the GitHub App manifest) | *Connect with …* fails | enter the client id and secret again with *Set up OAuth app* in Settings → **Git** or **Services** (for the GitHub App the manifest made, generate a new client secret in its settings on GitHub), or set `GITHUB_*` / `GITLAB_*` / `BITBUCKET_*` in `.env` |
| Plugin options marked secret | the plugin's **Configure** and its jobs fail | type those options again in **Plugins** → **Configure** |
| The OIDC signing key (deploys into a connected cloud account) | deploys that exchange the platform's token fail | delete the sealed key so the API makes a new one on the next deploy: `docker compose exec -T postgres psql -U action_platform action_platform -c 'DELETE FROM signing_key'`; the clouds read the new key from `<PUBLIC_URL>/.well-known/jwks.json` |
| Google sign-in and OAuth round trips in flight | expire | start them again |

There is no previous-key fallback: rotating the secret on purpose has the same effect as losing it.

## Rotating secrets

### `AP_API_TOKEN`

Only the API reads it: requests without a session or a token of their own must present it as `Authorization: Bearer` (your scripts or monitoring, if any). The web app and the workers in the compose files do not send it. No data depends on it.

```bash
openssl rand -hex 32 > secrets/api_token
docker compose up -d --force-recreate api worker worker-deploy
```

On Dokploy: new value for `AP_API_TOKEN` under *Environment*, **Deploy**. Give the new value to whatever called the API with the old one.

### The Postgres password

Postgres keeps the password it was initialised with in `pgdata`; the secret file only seeds a new volume. Change it in the database, then in the file, then recreate what reads it:

```bash
NEW="$(openssl rand -hex 32)"
docker compose exec -T postgres psql -U action_platform -d action_platform -c "ALTER USER action_platform PASSWORD '$NEW'"
printf '%s\n' "$NEW" > secrets/postgres_password
docker compose up -d --force-recreate
```

Inside its container `psql` connects over the local socket without a password, so the order is safe. With PgBouncer, update `POSTGRES_PASSWORD` in `.env` too. On Dokploy: `docker exec -i $(docker ps -qf name=ap-postgres) psql -U action_platform -d action_platform -c "ALTER USER action_platform PASSWORD '<new>'"`, then set `POSTGRES_PASSWORD` to the same value under *Environment* and **Deploy**.

### `BETTER_AUTH_SECRET`

Rotating it after a leak invalidates everything in [losing the auth secret](#losing-the-auth-secret); plan for every member to sign in again and for an owner to reconnect hosts, CI servers, OAuth apps and secret plugin options.

```bash
openssl rand -hex 32 > secrets/better_auth_secret
docker compose up -d --force-recreate api worker worker-deploy
docker compose exec -T postgres psql -U action_platform action_platform -c 'DELETE FROM signing_key'
```

Then work through the recovery column of the table above. On Dokploy: new `BETTER_AUTH_SECRET` under *Environment*, **Deploy**, and the `DELETE` through `docker exec` into `ap-postgres`.
