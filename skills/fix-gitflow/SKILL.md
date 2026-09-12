---
name: fix-gitflow
description: Diagnose and repair a branch that violates git-flow — wrong name, bad commit messages, commits on a protected branch — before it reaches a pull request.
---

# Fixing git-flow violations

1. `gitflow_audit`. Each problem names what is wrong; `gitflow_rules` explains the rule.
2. Wrong branch name: `git branch -m <kind>/<code>-slug` keeps the commits. Propose the name; rename only on approval.
3. Commits directly on `main`/`develop`: move them — `start_branch` from the same base, then `git cherry-pick` the commits and reset the protected branch to origin. Explain that this rewrites the local protected branch and get a yes.
4. Non-conventional messages: `git rebase -i` to reword, or `git commit --amend` for the last one. Show the new messages before rewriting; never rewrite commits already pushed to a shared branch without saying so.
5. Missing hooks (violations got through): `install_hooks`, then re-run `gitflow_audit` until it reports ok.
