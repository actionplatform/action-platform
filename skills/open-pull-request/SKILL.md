---
name: open-pull-request
description: Turn the current branch into a pull request — audit git-flow, preview target, title and body, open it only after the user approves.
---

# Opening a pull request

1. `propose_pull_request`. It audits git-flow (use the fix-gitflow skill when it refuses), picks the target from the rules — `feature`/`bugfix`/… → `develop` (or the default branch), `release`/`hotfix` → `main` — and drafts title and body from the commits, grouped like the changelog.
2. Show head → base, the title and the body. Adjust `title` or `base` on request; `base` must still be allowed by git-flow.
3. On approval, `open_pull_request` with the same arguments (`draft=true` when the user wants a draft). The branch is pushed first if it is not on origin yet.
4. Report the URL. CI runs `code-quality`, `commits`, `gitflow` and `trivy` on it.
5. For `release`/`hotfix` branches, remind the user a second PR into `develop` follows after the first merges.
