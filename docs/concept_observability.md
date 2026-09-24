# Observability

Every component reports to [Sentry](https://sentry.io) when given a DSN, and stays silent otherwise. Use one Sentry project per component so releases and issues do not mix: `cli`, `api`, `web`. The Python ones — CLI, MCP server, API — all start through `action_platform.bootstrap`: `.env` first, then Sentry.

| Component | Variable | Release tag | Extra |
|---|---|---|---|
| API | `AP_SENTRY_DSN` | `api@<version>` (the api component version) | always installed |
| CLI | `AP_SENTRY_DSN` | `cli@<version>` | opt-in: `pip install "action-platform[sentry]"` and export the DSN |
| MCP server | `AP_SENTRY_DSN` | `mcp@<version>` | same as the CLI |
| Web | `SENTRY_DSN` | `web@<version>` | `@sentry/nextjs`; browser, server and edge |

With the compose files and Dokploy, set `AP_SENTRY_DSN_API` and `AP_SENTRY_DSN_WEB` in `.env`; they reach the containers under the names above.

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
