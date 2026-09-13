# Observability

Every component reports to [Sentry](https://sentry.io) when given a DSN, and stays silent otherwise. Use one Sentry project per component so releases and issues do not mix: `cli`, `api`, `web`.

| Component | Variable | Release tag | Extra |
|---|---|---|---|
| API | `AP_SENTRY_DSN` | `api@<version>` (the api component version, `action_platform/api/LAST_VERSION`) | installed with `pip install "action-platform[api]"` |
| CLI | `AP_SENTRY_DSN` | `cli@<version>` | opt-in: `pip install "action-platform[sentry]"` and export the DSN |
| Web | `SENTRY_DSN` | `web@<version>` | `@sentry/nextjs`; browser, server and edge |

With the compose files and Dokploy, set `AP_SENTRY_DSN_API` and `AP_SENTRY_DSN_WEB` in `.env`; they reach the containers under the names above.

## What is sent

- Unhandled exceptions and HTTP 5xx, with the request route (never the body) and the release. In the web app every server action that answers `{ ok: false }` also reports the underlying error unless it is an expected API answer below 500 (`lib/result.ts`).
- Python `logging` records at warning and above, as Sentry logs.
- Traces for a sample of requests — `AP_SENTRY_TRACES_SAMPLE_RATE` / `SENTRY_TRACES_SAMPLE_RATE`, default `0.1`.
- In the browser, a session replay only when an error happens, with all text masked and media blocked.

`send_default_pii` / `sendDefaultPii` are off: no IPs, cookies, headers or user identifiers. Code-host tokens never enter a request body that Sentry could see — they travel in the `credentials` field of API requests, which the SDK does not capture.

The environment defaults to `production`; set `AP_SENTRY_ENVIRONMENT` / `SENTRY_ENVIRONMENT` to tell staging apart.

## Web details

The browser needs the DSN without a rebuild, so the root layout renders it as `<meta name="sentry">` from the runtime `SENTRY_DSN` and `instrumentation-client.ts` reads it there — no `NEXT_PUBLIC_*` baked into the image. `instrumentation.ts` forwards every server-side request error to Sentry after logging it as JSON, and `app/global-error.tsx` catches what escapes the root layout.

Source maps upload only when `SENTRY_AUTH_TOKEN`, `SENTRY_ORG` and `SENTRY_PROJECT` are present at build time; the published images do not upload them.

## CLI details

The CLI initialises Sentry in `action_platform/main.py` through `action_platform/observability.py` when both the SDK and `AP_SENTRY_DSN` are present. Nothing is reported from a developer's machine unless they choose to export the DSN.
