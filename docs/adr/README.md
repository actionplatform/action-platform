# Architecture decisions

One file per decision, numbered, never edited after acceptance — a later decision supersedes it and says so. Each states the context, the decision and what it cost. The index below is the reading order.

| # | Decision | Status |
|---|---|---|
| [0001](0001-release-table.md) | `release` is the platform's table, one row per tag, any source | accepted |
| [0002](0002-targets-and-executors.md) | A deploy target is *where*; the executor is *who*; a deployment always references a release | accepted |
| [0003](0003-snapshot-reads.md) | App pages read a snapshot; git stays on writes and on the worker | accepted |
| [0004](0004-server-pages.md) | Lists are paged on the API, never in the browser | accepted |
| [0005](0005-one-data-table.md) | One `DataTable` with fixed dimensions for every list | accepted |
| [0006](0006-ci-providers-in-the-library.md) | CI runners and host readers live in the library, not the API | accepted |
| [0007](0007-queue-on-postgres.md) | The job queue is a Postgres table, woken by NOTIFY, split light/heavy | accepted |
| [0008](0008-release-readiness.md) | A release knows whether it can reach a stage before anyone deploys it — checks per stage, stored, gating the deploy | accepted |
