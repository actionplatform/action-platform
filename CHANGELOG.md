# Changelog

## v0.1.1 — 2026-09-12

### Docs
- absolute cover image URL so it renders on PyPI

## v0.1.0 — 2026-09-12

### Features
- **mcp:** propose_pull_request and open_pull_request tools
- **cli:** pr command
- **pr:** propose and open pull requests from git-flow branches
- **install:** copy hooks into .git/hooks instead of a tracked .githooks
- **hooks:** bundle git hooks in the package
- dogfood devtool config + improve CLI UX
- initial devtool scaffolding

### Docs
- pr command
- **skills:** open-pull-request replaces prepare-pull-request
- **mcp:** skills and tool help reflect hooks in .git/hooks
- **cli:** help text reflects .git/hooks

### Tests
- **pr:** proposal, targets, refusals, open
- **install:** hooks land in .git/hooks and refresh from the package

### CI
- **trivy:** pin trivy-action to v0.36.0

### Chores
- **platform:** PyPI metadata and reset version before first release
- **release:** 0.1.1
- **platform:** update hooks
- untrack PLAN.md and drop reference from README

## v0.1.1 — 2026-09-12

### Chores
- **platform:** update hooks
