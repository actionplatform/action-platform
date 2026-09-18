# 0003 — App pages read a snapshot

**Status**: accepted · 2026-09-18 · [#247](https://github.com/actionplatform/action-platform/issues/247)

## Context

`GET /apps/{id}`, commits, branches, tags, releases and manifest each opened the app's clone. The first view cloned the repository; every replica kept its own clones; a private repository without credentials on a GET failed; the API could not scale by replicas nor run on Lambda.

## Decision

`app_snapshot` holds what the pages read, taken from the clone after every change the platform makes (sync, release, push, branch, checkout, commit, configuration) and on the first read of an app that has none. GET routes answer from the row. Git stays on writes and on the worker.

## Consequences

Reads are stateless and indexed. A change made outside the platform shows after the next sync — or within seconds through the host's webhook ([0007](0007-queue-on-postgres.md)). `detail.clean` stays live from the drafts table.
