# 0004 — Lists are paged on the API

**Status**: accepted · 2026-09-18 · [#235](https://github.com/actionplatform/action-platform/issues/235)

## Context

The first lists fetched everything and sliced in the browser. With hundreds of runs per app that is bandwidth, memory and a wrong total.

## Decision

Every list that grows takes `page` and `per` (1–100, default 10) and answers `items`, `total`, `page`, `per`: releases, pull requests, CI runs, jobs. The URL carries both; the page component fetches the slice; nothing is paged in the browser.

## Consequences

`usePagination` is gone. Adding a list means adding a paged route first.
