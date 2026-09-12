---
name: prepare-pull-request
description: Get a branch ready to merge — audit git-flow, confirm the right target, summarize the changes for the PR description.
---

# Preparing a pull request

1. `gitflow_audit` — must be ok. Otherwise use the fix-gitflow skill first.
2. Target from `gitflow_rules`: `feature`/`bugfix`/`chore`/… → `develop` (or the default branch when there is no develop); `release`/`hotfix` → `main`, then a second PR into `develop`. CI refuses anything else.
3. Draft the description from the commits: one line per Conventional Commit, grouped like the changelog (Features, Bug Fixes, …). Title is the branch's main intent in the same format (`feat(login): password reset`).
4. Hand the title, target and description to the user; opening the PR is theirs (or `gh pr create`) — the platform does not open PRs yet.
