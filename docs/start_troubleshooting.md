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

**`the proxy does not know <org>/<project>/<app> yet, and this deploy may not register it`** — the first deploy of an app on `aws/lambda` registers it on the deploy proxy and needs `org.manage`. Ask an owner or admin of the organization to deploy once (their token carries the scope), or run `action-platform aws-lambda proxy create` with a logged-in CLI. Later deploys by any deployer go through.

**Preflight or deploy says the proxy is unreachable, or `AP_AWS_LAMBDA_PROXY_URL` is missing** — the organization has no proxy URL. Plugins → **AWS Lambda** → **Configure** → *Deploy proxy URL*; `action-platform aws-lambda proxy health <url>` checks a URL from a terminal. Installing the proxy is in the [apx-aws-lambda](https://github.com/actionplatform/apx-aws-lambda) README.

**`AccessDenied` on `AssumeRole` right after the app was registered** — IAM propagation. The proxy retries for a few seconds; when that is not enough, run the deploy again.

**`sam build` fails with a missing tool (`go`, `mvn`, `bundle`…)** — the worker builds inside the API image, which carries Go, Node, JDK + Maven and Ruby. A self-built image without them cannot build that language; use the published image or add the toolchain ([self-hosting](start_self_hosting.md)).

**`no space left on device` on the worker** — clones, SAM build artifacts and images fill the host. `docker system prune` on the machine that runs the worker, and give `/var/lib/docker` room.

**`/health` answers 404, `/ping` answers something unexpected** — API Gateway reserves `/ping` on the execute-api domain; the templates expose `/health`. An app generated before the change still routes `/ping` in its own code, but the gateway answers first: rename the route.

**Tear down failed** — the `destroy` job could not delete a stack (a resource CloudFormation refuses to delete, a stack already gone by hand). The app stays on the platform with the error on its history. Fix the stack in the AWS console, then delete again; or delete without *Also tear down* and remove the stack yourself.

## Git hosts

**`token rejected by GitHub (401); reconnect the host`** — the stored token expired or was revoked. Settings → **Git**: *Remove host* on that account, then **Connect with …** again.

**A deploy fails with `403: Resource not accessible by integration`** — the GitHub App lacks *Actions: Read and write*, which dispatching `publish.yml` needs. GitHub › Settings › Developer settings › GitHub Apps › the app › Permissions & events → Repository permissions → Actions → Read and write → Save; then on the installation (organization › Settings › GitHub Apps) accept the new permissions. Settings › Integrations on the platform lists the problem until it is done.

**Deleting a repository is refused** — a GitHub OAuth host connected before the `delete_repo` scope existed cannot delete; remove the host and connect it again. A GitHub App needs *Administration* (the one created by the wizard has it). Bitbucket needs the *repositories: delete* permission on the consumer. Nothing on the platform is removed when the host refuses.

**The wizard offers no organization to own the repository** — the GitHub App is installed on no account, or on one without permission to create repositories. *Install on another organization* under Settings → Git; an app created as private must be made public under GitHub → Developer settings → GitHub Apps → Advanced.

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

**Invitation link does not work** — links live seven days and are bound to the invited email; sign in with that address, or ask for a new invitation from Organization → Members.

## Platform

**`ready: false` / `database: behind` on `GET /api/version`** — the schema is behind and `AP_DATABASE_AUTO_MIGRATE=0` stops the processes from migrating. Run `action-platform-api db migrate` (the compose files do it in the `migrate` service) — [database](concept_database.md).

**The setup wizard says the API is unreachable or has no auth secret** — the web and the API must share `AP_DATABASE_URL` and `AP_AUTH_SECRET`; the wizard prints the exact values to start the API with when running by hand ([self-hosting](start_self_hosting.md)).

**A job stays `running` for ever** — the worker died mid-job. After thirty minutes the reaper puts it back in the queue with `worker lost`; a job that fails three times ends `failed` with the last error.

**The web shows stale data** — lists poll every few seconds while a job is live; a page reload re-reads everything. An app older than `AP_WORKSPACE_TTL` seconds is re-cloned on the next request; **Sync** forces it now.

## Still stuck

`action-platform diagnose` on the repository prints the target's view: health, last deploy, where the logs are. Open an issue with the command or the job id, the message and the log — [security](../SECURITY.md) for anything that looks like a vulnerability.
