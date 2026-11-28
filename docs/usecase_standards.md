# Development standards

Keep every repository on the same branch, commit and pull request rules, and enforce them instead of documenting them.

## Context

Several teams work across many repositories. Some use git-flow, some trunk-based development, some no convention at all.

## Challenge

Written guidelines drift. Commit messages cannot feed a changelog when half of them say "fix". Pull requests target the wrong branch. Someone pushes straight to `main`. Reviewers spend time on conventions instead of code.

## Solution

Every app follows one git-flow, enforced in layers:

| Layer | Refuses |
|---|---|
| git hooks (`pre-commit`, `commit-msg`, `pre-push`) | a commit on `main`, `master` or `develop`, a branch name that is not `<kind>/<code>[-slug]`, a message that is not a Conventional Commit |
| CI (`gitflow`, `conventional-commit` jobs) | the same, on the pull request, when hooks were skipped |
| the code host (`[gitflow.protection]`) | direct pushes, force pushes and deletions of protected branches; required checks before merge |
| the CLI and MCP tools | they pick the base branch and the pull request target from the branch kind |

`AGENTS.md` in every repository states the same rules for people and AI agents.

## Workflow

1. `action-platform branch feature 42 login` starts `feature/42-login` from the right base and installs the hooks.
2. Commits follow Conventional Commits; the hooks refuse the rest.
3. `action-platform gitflow` audits the branch before the pull request.
4. `action-platform pr` opens the pull request to the target the rules allow, with a body built from the commits.
5. The release changelog is generated from those same commit messages.

## Benefits

- Rules are checked by machines on every commit and pull request.
- Changelogs come for free because every commit has a type.
- Repositories with years of history in another style are audited only from the commit that added `platform.toml`; nobody rewrites history.
- The organization sets a default for branch protection, and each app can follow it or override it.

## Related features

[Git-flow](concept_git_flow.md) · [Releases](concept_releases.md) · [Adopting repositories](use_adopting.md) · [platform.toml](concept_manifest.md)

## Getting started

In an existing repository, run `action-platform install` to add `platform.toml`, the hooks, the quality config and the CI checks, then `action-platform gitflow --install-hooks` on every clone. On the hosted platform, use **Adoption** on the project page.
