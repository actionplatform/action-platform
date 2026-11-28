# Troubleshooting

What the platform says when it refuses something, what it means and what to do. Messages are quoted as the CLI prints them and as the web shows them in a dialog or on a job's row; the API returns the same text in `detail`.

## Where to look

| Surface | Where the error is |
|---|---|
| web | the dialog that refused, the alert on the card, or the job's row under **Deployment history** (expand it: summary, *View logs*, *Copy error*) |
| CLI | stdout: the message, and the output of the git or target command that failed |
| API | the JSON body: `{"detail": "…"}` with the HTTP status; `GET /api/v1/jobs/{id}` for a job's `error` and `result` |
| worker | its log (`docker compose logs worker`); Sentry when `AP_SENTRY_DSN` is set ([observability](concept_observability.md)) |

## Releases

**`working tree is dirty — commit or stash first`** — a release and a deploy refuse a clone with uncommitted changes. On the platform this means pending edits: **Commit changes** or **Discard changes** on Configuration, then retry.

**`tag vX.Y.Z already exists`** / **`X.Y.Z is already the current version`** — the version was released before, locally or on `origin`. Pick the next increment, or delete the stale tag on the remote when the earlier release was undone by hand.

**Release refused: branch not on the remote** — the platform releases from a branch the remote knows. Push the branch (Activity → *Push to remote*) or release from `main`/`master`.

**The release is `X.Y.Z-rc.N`, not `X.Y.Z`** — you released off `main`/`master`. Pre-releases come from every other branch; merge and release from the default branch for a stable version ([releases](concept_releases.md)).

**`CI <name> failed`** — the release commit was made and pushed but the CI runner the release triggers reported a failure; the tag exists. Fix and release the next patch.

## Deploys

**`a deploy to <stage> is already queued|running; wait for it to finish`** (`409`) — one deploy per environment at a time; the web disables the button meanwhile. Deploy to the other stage or wait ([deployments](concept_deployments.md#stages)).

**`a deploy ships a release: pass the version to deploy, or check out a release tag`** / **`no release 'X.Y.Z': tags are … — release first`** — nothing to deploy. Create a release first; the web's Deploy card lists the releases and stays empty until there is one.

**`no deploy target configured — run action-platform cloud set <cloud>`** — `platform.toml` has no `[deploy] target`. In the web: Configuration → **Deploy target**; from the CLI: `action-platform cloud set aws/lambda`.

**`AccessDenied` on `AssumeRoleWithWebIdentity`, or `AP_AWS_LAMBDA_ROLE_ARN` is missing** — the organization has not connected its AWS account, or the role's trust does not match: Connect → Deploy → **AWS Lambda** → **Configure** → *AWS account ID* must be the connect stack's account (or its `DeployRoleArn`), and the stack's `IssuerUrl` and `Organization` must be this platform's public url and the organization's slug. Connecting the account is in the [apx-aws-lambda](https://github.com/actionplatform/apx-aws-lambda) README.

**Readiness says `template.yaml has no PermissionsBoundaryArn parameter`** — the app's overlay predates connected accounts. Apply it again: Configuration → **Deploy target**, or `action-platform cloud set aws/lambda`.

**`sam build` fails with a missing tool (`go`, `mvn`, `bundle`…)** — the workers run on the `action-platform-worker` image, which carries Go, Node, JDK + Maven and Ruby; the `api` image has none of them. A worker started on the api image, or a self-built image without them, cannot build that language; use the published image or add the toolchain ([self-hosting](start_self_hosting.md)).

**`no space left on device` on the worker** — clones, SAM build artifacts and images fill the host. `docker system prune` on the machine that runs the worker, and give `/var/lib/docker` room.

**`/health` answers 404, `/ping` answers something unexpected** — API Gateway reserves `/ping` on the execute-api domain; the templates expose `/health`. An app generated before the change still routes `/ping` in its own code, but the gateway answers first: rename the route.

**Tear down failed** — the `destroy` job could not delete a stack (a resource CloudFormation refuses to delete, a stack already gone by hand). The app stays on the platform with the error on its history. Fix the stack in the AWS console, then delete again; or delete without *Also tear down* and remove the stack yourself.

## Git hosts

**`token rejected by GitHub (401); reconnect the host`** — the stored token expired or was revoked. Connect → **Git**: *Remove host* on that account, then **Connect with …** again.

**A deploy fails with `401: Requires authentication`** — the app points at no source host and no connected host matches its repository's URL (a public repository still syncs, git needs no token there). A host that was removed and reconnected is taken over by itself: the app moves to the connected host its repository's URL belongs to. Otherwise App › Settings › Source host: pick the connection; the deploy dispatches the workflow with its token.

**A deploy fails with `403: Resource not accessible by integration`** — the GitHub App lacks *Actions: Read and write*, which dispatching `publish.yml` needs. GitHub › Settings › Developer settings › GitHub Apps › the app › Permissions & events → Repository permissions → Actions → Read and write → Save; then on the installation (organization › Settings › GitHub Apps) accept the new permissions. Settings › Integrations on the platform lists the problem until it is done.

**Deleting a repository is refused** — a GitHub OAuth host connected before the `delete_repo` scope existed cannot delete; remove the host and connect it again. A GitHub App needs *Administration* (the one created by the wizard has it). Bitbucket needs the *repositories: delete* permission on the consumer. Nothing on the platform is removed when the host refuses.

**The wizard offers no organization to own the repository** — the GitHub App is installed on no account, or on one without permission to create repositories. *Install on another organization* under Connect → Git; an app created as private must be made public under GitHub → Developer settings → GitHub Apps → Advanced.

**`cannot read owner/name: the code host refused the connected account`** when adding a repository — the connected account cannot read it, often a private repository of an organization while public ones work. With a GitHub OAuth host, the organization may restrict third-party OAuth apps: an owner approves the app under the organization › Settings › Third-party access. With the GitHub App, install it on that organization with access to the repository (*Install on another organization* under Connect → Git). Otherwise remove the host and connect it again with an account that can read private repositories.

**Import lists no teams or people** — the GitHub App lacks *Organization › Members (read)* (add it under the app's settings on GitHub and accept it in the organization), or the OAuth token has no `read:org`.

**Pull requests and releases are missing on the app** — they arrive with the `import` job queued after every sync, release and push. **Sync** the app, then look at the job on `GET /api/v1/jobs?app=<id>`.

## Git-flow

**The hook refuses a commit** — the message is not a Conventional Commit (`feat(scope): subject`), or the branch is `main`/`master`/`develop`, where the rules forbid committing. `action-platform branch <kind> <code> [slug]` starts a branch of the right kind from the right base ([git-flow](concept_git_flow.md)).

**`cannot find a default branch (main or master)`** — the repository has neither. Create and push one; the platform reads the default branch from the remote.

**The app opened on a branch I did not choose** — a pull request merged on the host deletes its branch, and the next sync sends the app back to the default branch. Start a new branch for further work.

## Access

**`403` from `/api/v1`, "not available for your role"** — every call needs your role in the organization *and* the token's scope: a `developer` with a `release` token cannot release; an `owner` with a `read` token can only look. `action-platform whoami` prints both; log in again with a wider scope if your role allows it ([access control](concept_access_control.md)).

**The device code expired** — codes live ten minutes. Run `action-platform login <url>` again and approve the new code at `/device`.

**A token sees one app only** — its reach was limited to a project or an app when approved. Log in again and approve **All organizations** or the organization alone.

**Invitation link does not work** — links live seven days and are bound to the invited email; sign in with that address, or ask for a new invitation from Team → Members.

## Platform

**`ready: false` / `database: behind` on `GET /api/version`** — the schema is behind and `AP_DATABASE_AUTO_MIGRATE=0` stops the processes from migrating. Run `action-platform-api db migrate` (the compose files do it in the `migrate` service) — [database](concept_database.md).

**The setup wizard says the API is unreachable or has no auth secret** — the web and the API must share `AP_DATABASE_URL` and `AP_AUTH_SECRET`; the wizard prints the exact values to start the API with when running by hand ([self-hosting](start_self_hosting.md)).

**The setup wizard refuses the setup token** (`403 setup_token`) — print it again in the API container (`docker compose exec api action-platform-api setup token`; on Dokploy in the `ap-api` terminal). It follows the auth secret: a token printed before `BETTER_AUTH_SECRET` changed no longer works, and `AP_SETUP_TOKEN`, when set, replaces it. `setup is closed` from the command means an account exists: sign in at `/login`.

**A job stays `running` for ever** — the worker died mid-job. After thirty minutes the reaper puts it back in the queue with `worker lost`; a job that fails three times ends `failed` with the last error.

**The web shows stale data** — lists poll every few seconds while a job is live; a page reload re-reads everything. An app older than `AP_WORKSPACE_TTL` seconds is re-cloned on the next request; **Sync** forces it now.

## Self-hosting

**`docker compose up` (or a Dokploy deploy) stops with `dependency failed to start: container …postgres… is unhealthy`** — Postgres never became healthy, so `migrate`, `api` and the workers never start. On a first start it refuses an empty password: `POSTGRES_PASSWORD` on Dokploy, `secrets/postgres_password` with the compose file (its log says `superuser password is not specified`). A full disk stops it too. `docker compose logs postgres` names the cause; fix it and run `docker compose up -d` again.

**`email is not configured: set AP_SMTP_HOST`** (`503` from `POST /api/auth/password/forgot`) — the API has no SMTP server, so it cannot send the reset link; the login page also hides *Forgot your password?* in that case. Set `AP_SMTP_HOST` and the other `AP_SMTP_*` variables ([environment](start_self_hosting.md#environment)) and recreate the `api` container. With SMTP set, a reset that cannot be sent still answers `202` so the form does not reveal which emails have accounts; the failure is logged by the API, and Admin → Instance has **Send test email** to check the server.

**Google answers `Error 400: redirect_uri_mismatch`** — the OAuth client's *Authorized redirect URIs* do not contain the exact address the platform sends: `${PUBLIC_URL}/api/sign-in/google/callback`, built from `PUBLIC_URL` (scheme, host and port included, no trailing slash). Add that URI to the client in Google Cloud, or fix `PUBLIC_URL` and recreate `api` and `web`.

**Jobs stay `queued`** — no worker takes them: the `worker` and `worker-deploy` containers are stopped or crash on start. Syncs, releases, pushes and imports wait for `worker`; deploys, readiness and tear-downs wait for `worker-deploy`. `GET /api/health` answers `503` with `workers.light` or `workers.deploy` false while one of them is missing, owners see each worker and the queue under Admin → Instance, and the job row in the web says "No worker is running for <kind> jobs" after two minutes. `docker compose ps` (a worker without a recent heartbeat is `unhealthy`) and `docker compose logs worker worker-deploy`; on Dokploy the `ap-worker` and `ap-worker-deploy` services.

## Still stuck

`action-platform diagnose` on the repository prints the target's view: health, last deploy, where the logs are. Open an issue with the command or the job id, the message and the log — [security](../SECURITY.md) for anything that looks like a vulnerability.
