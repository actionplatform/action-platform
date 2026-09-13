# Changelog

## v0.3.0 — 2026-09-13

### Features
- import a repository without platform.toml — install on add from the web, CLI/MCP, then commit on a branch with a pull request
- **api:** template sources — merged matrix, init/cloud/service from a custom repository, remote flow and configuration tools

### Bug Fixes
- **install:** name platform.toml after the repository; skip the code-quality workflow when there is no language
- **templates:** plain repositories get a Repositories category and resolve without a stack

## v0.2.1 — 2026-09-13

### Bug Fixes
- **api:** clone and sync private repositories with the source host credentials

## v0.2.0 — 2026-09-13

### Features
- **api:** modular api/v1 with configuration, flow, branch-aware release and resilient sync

### Style
- ruff format api services and tests

### Chores
- strip comments from source, configs and workflows; nextCookies last

## v0.1.2 — 2026-09-12

## v0.1.1 — 2026-09-12

### Features
- **release:** --component on the CLI, MCP and API
- **api:** apps by git url in workspaces, init from templates, push, per-request source credentials, --reload
- **api:** JSON API over the core — projects registry, git-flow, commits, branches, tags, release and deploy

### Chores
- **platform:** declare web and api release components
