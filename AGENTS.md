# AGENTS.md

Rules an AI agent (or a new contributor) follows in this repo. Added by `action-platform install`; keep it current.

## Commits

[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/): `type(scope)!: description` — `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. One commit per concern; stage files explicitly — never `git add .`. Enforced by `.githooks/` and CI.

## Branches

Git-flow: work on `<kind>/<code>[-slug]` started with `action-platform branch <kind> <code>`. Kinds: `feature bugfix hotfix release support chore docs refactor test ci perf`. Never commit on `main`, `master` or `develop`; `feature`/`bugfix` merge into `develop`, `release`/`hotfix` into `main` and `develop`.

## Platform

`platform.toml` declares the project; `action-platform release` cuts versions from `LAST_VERSION`; `action-platform gitflow` audits a branch before a pull request.

## Layout

The API is layers (`api/routes → services → repositories → schemas → core`) and every layer has a folder per context (activity, releases, deployments, configuration, projects, templates, organization, integrations, auth, identity, jobs); the web app has `features/<context>`. New code goes in the context folder of each layer — never a new top-level module, never a route that reaches a repository directly, never a feature importing another feature's internals. `.importlinter` and ESLint enforce it; [docs/contribute_architecture.md](docs/contribute_architecture.md) has the map.
