---
name: diagnose
description: Check the health, status and URL of a deployed project without changing anything.
---

# Diagnosing

Read-only.

1. `project_info` for the target and stage in play.
2. `diagnose` with the `stage` the user cares about (default follows the branch).
3. Report `status`, `url` and `details`. If `ok` is false, suggest the next step: `deploy` for a failed rollout, the add-cloud skill when no target is set, `DEPLOY.md` when credentials are missing.
