# 0001 — `release` is the platform's table

**Status**: accepted · 2026-09-18 · [#229](https://github.com/actionplatform/action-platform/issues/229)

## Context

`release` was a copy of the code host's releases. A tag without a GitHub Release, a plain git server, or an import that had not run yet left no row, so a deployment could only name its release by string.

## Decision

One row per `(app, tag)`, whatever named it first: `platform` when cut here, the host (`github`, `gitlab`, `bitbucket`, any importer) when it published one, `git` when the tag simply exists in the clone. Rows merge by tag; a host or the platform enriches what git alone knew, git never overrides a host. Each row carries `component` and `version`. `deployment.release_id` references it.

## Consequences

A tag always has a row, so "a deployment references a release" is a foreign key, not a convention. The clone's tags are scanned on every sync (cheap: `for-each-ref`). Source is an open string — a new importer needs no schema change.
