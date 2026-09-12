---
name: deploy
description: Ship the current version to the [deploy] target — preflight first, real deploy only on approval, then verify.
---

# Deploying

`deploy` defaults to `dry_run=true`, which runs preflight only: tooling, template validation, credentials.

1. `project_info` — `[deploy] target` must exist; if not, use the add-cloud skill.
2. `deploy` (dry run) with the `stage` the user named. Surface any error verbatim; "no provider installed" means the target's provider package is missing.
3. On approval, `deploy` with `dry_run=false`. Report the URL.
4. `diagnose` afterwards and report status.
