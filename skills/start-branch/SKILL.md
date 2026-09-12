---
name: start-branch
description: Start work on a git-flow branch — pick the kind from what the user is doing, derive the code from the issue, let start_branch choose the base.
---

# Starting a branch

Never work directly on `main`, `master` or `develop`; the hooks refuse it anyway.

1. Pick the kind from the intent, not from the words: new capability → `feature`; bug found in development → `bugfix`; bug in production that must ship now → `hotfix`; preparing a version → `release` (code is the version, e.g. `1.4.0`); everything else by Conventional Commit type: `chore`, `docs`, `refactor`, `test`, `ci`, `perf`. `gitflow_rules` lists them.
2. Code is the issue or ticket the user named (`42`, `PROJ-123`). Ask when there is none — a branch without a code is not allowed.
3. Slug is optional: two or three words, `start_branch` normalizes them.
4. `start_branch`. It checks out `develop` (or the default branch when there is no develop; `main` for hotfix/release), pulls, creates and pushes.
5. Report branch and base. When the work is done, the open-pull-request skill closes the loop. A dirty tree or an existing name comes back as an error — relay it, do not stash or delete for the user.
