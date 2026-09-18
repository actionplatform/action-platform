# 0002 — Targets and executors

**Status**: accepted · 2026-09-18 · [#226](https://github.com/actionplatform/action-platform/issues/226)

## Context

`[deploy] target = "aws/lambda"` meant both *where* the app goes and *the worker runs it*. What a GitHub Actions workflow publishes to PyPI or a Jenkins job pushes to a registry was invisible.

## Decision

`[[deploy.targets]]` declares several targets per app, each with `run_by`: `platform`, `github_actions`, `jenkins` or `manual`. The platform executes only its own; the others it *observes* — their runs become `deployment` rows — and *verifies* (`DeployTarget.verify(version)`) at the destination: PyPI, npm, a registry, the stack. **A deployment always references a release**: a run on a branch without a tag is not a deployment; a manual record without a version is refused.

## Consequences

Built-in `pypi`, `npm`, `docker` kinds never deploy. The Deployments tab lists the platform's runs; what every target received is on the API, CLI and MCP. Status `verified` means the version was found where it should be, whoever ran the pipeline.
