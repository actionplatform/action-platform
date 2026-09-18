# 0006 — CI runners and host readers in the library

**Status**: accepted · 2026-09-18 · [#220](https://github.com/actionplatform/action-platform/issues/220), [#239](https://github.com/actionplatform/action-platform/issues/239)

## Context

Talking to GitHub, GitLab, Bitbucket and Jenkins was split: the API had its own importers (`ImportSource`), the library its own `SourceHost`. Two houses for one job; the CLI could not read what the API could.

## Decision

`action_platform/providers/ci/` mirrors `providers/source/`: `CIRunner` (Jenkins, GitHub Actions, GitLab CI, Bitbucket Pipelines) with `runs`, `start`, `test`. `SourceHost` gains `releases()` and `pull_requests()`. The API builds a provider from the host's credentials and reads through it; its `ImportSource` is gone. Plugins can add runners through the `action_platform.ci_runner` entry point.

## Consequences

The API's `core/abc` keeps only `HostProvider` (OAuth) and `HostDirectory` (org import), the two things that are hosted-only. The CLI and MCP get releases, pull requests and CI runs of a host for free.
