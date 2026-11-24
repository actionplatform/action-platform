# Observability

Every component reports to [Sentry](https://sentry.io) when given a DSN, and stays silent otherwise. Use one Sentry project per component so releases and issues do not mix: `cli`, `api`, `web`. The Python ones — CLI, MCP server, API — all start through `action_platform.bootstrap`: `.env` first, then Sentry.

| Component | Variable | Release tag | Extra |
|---|---|---|---|
| API | `AP_SENTRY_DSN` | `api@<version>` (the api component version) | always installed |
| CLI | `AP_SENTRY_DSN` | `cli@<version>` | opt-in: `pip install "action-platform[sentry]"` and export the DSN |
| MCP server | `AP_SENTRY_DSN` | `mcp@<version>` | same as the CLI |
| Web | `SENTRY_DSN` | `web@<version>` | `@sentry/nextjs`; browser, server and edge |

With the compose files and Dokploy, set `AP_SENTRY_DSN_API` and `AP_SENTRY_DSN_WEB` in `.env`; they reach the containers under the names above.

## Instance health

Sentry reports what went wrong; the instance also answers whether it is able to work.

- **`GET /api/health`** — no token, no details. `200 {"status": "ok", ...}` when the database answers, the migrations are at head and a worker was seen in the last minute for each of the two kind groups; `503` with the same body otherwise: `{status, database, migrations, workers: {light, deploy}}`. `light` is the worker that takes sync, release, push and the imports, `deploy` the one that takes deploy, readiness and tear-down. An instance run on purpose without one of them reports `503` for as long as it has none. It is a probe for a monitor; the containers' own checks stay on `/api/version`.
- **`GET /api/v1/instance/health`** — owners only. The same fields plus every worker (name, host, the kinds it takes, last seen), the queue per job kind (queued, running, age of the oldest queued job, whether a live worker takes that kind), whether email, Google sign-in, Sentry on the API and each code-host OAuth app are configured, the redirect URI Google must allow, the last email the API failed to send since it started, and the versions.
- **`POST /api/v1/instance/test-email`** — owners only. Sends a message to the signed-in owner and answers `{sent, to, error}`; on failure `error` carries the SMTP server's text.
- **Settings → Instance** in the web shows all of it, refreshed every ten seconds, with **Send test email**.

Workers write a heartbeat (table `worker`: name, kinds, host, started, last seen) every fifteen seconds, also while a long job runs; one silent for sixty seconds does not count, and rows older than a day are dropped when a worker starts. `action-platform-api worker --check --name <name>` exits `0` when the worker of that name is alive and `1` otherwise; it is the healthcheck of `worker` (`--name worker`) and `worker-deploy` (`--name deploy`) in the compose files. A job queued for more than two minutes with no live worker for its kind carries `no_worker: true`, and the web says "No worker is running for <kind> jobs" instead of waiting.

## What is sent

- Unhandled exceptions and HTTP 5xx, with the request route (never the body) and the release. In the web app every server action that answers `{ ok: false }` also reports the underlying error unless it is an expected API answer below 500 (`lib/result.ts`).
- Python `logging` records at warning and above, as Sentry logs.
- Traces for a sample of requests — `AP_SENTRY_TRACES_SAMPLE_RATE` / `SENTRY_TRACES_SAMPLE_RATE`, default `0.1`.
- In the browser, a session replay only when an error happens, with all text masked and media blocked.

`send_default_pii` / `sendDefaultPii` are off: no IPs, cookies, headers or user identifiers. Code-host tokens never enter a request body that Sentry could see — they travel in the `credentials` field of API requests, which the SDK does not capture.

The environment defaults to `production`; set `AP_SENTRY_ENVIRONMENT` / `SENTRY_ENVIRONMENT` to tell staging apart.

## Web and CLI details

The browser reads the DSN at runtime from the page, so no rebuild is needed to set or change it; server-side request errors are logged as JSON and forwarded. Source maps upload only when `SENTRY_AUTH_TOKEN`, `SENTRY_ORG` and `SENTRY_PROJECT` are present at build time; the published images do not upload them.

The CLI reports only when the SDK is installed and `AP_SENTRY_DSN` is exported — never from a developer's machine by default.
