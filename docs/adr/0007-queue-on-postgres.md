# 0007 — The job queue is a Postgres table

**Status**: accepted · 2026-09-18 · [#241](https://github.com/actionplatform/action-platform/issues/241), [#243](https://github.com/actionplatform/action-platform/issues/243), [#245](https://github.com/actionplatform/action-platform/issues/245), [#249](https://github.com/actionplatform/action-platform/issues/249)

## Context

Sync, release, deploy, push and imports run on a worker. A broker would be another service to run; polling every two seconds is latency; one worker held a ten-minute deploy while syncs waited.

## Decision

`job` stays a table claimed with `SELECT … FOR UPDATE SKIP LOCKED`. `enqueue` sends `NOTIFY ap_jobs`; a worker keeps a `LISTEN` connection and claims within milliseconds, falling back to the poll where the database cannot push. Two worker services share the queue — light kinds (sync, release, push, imports) and heavy (deploy, destroy) — each with a concurrency of its own; the `api` image carries no toolchains, the `worker` image does. Code-host webhooks enqueue the sync.

## Consequences

No broker. Postgres is the one stateful service; PgBouncer sits in front when replicas outgrow its connections. A job that dies is reaped and retried three times.
