---
name: edit-configuration
description: Change a hosted app's platform.toml, deploy target or services on the platform's clone, then commit on a git-flow branch and open the pull request in one call.
---

# Editing configuration on a hosted platform

Remote only (`action-platform mcp --remote`). Every edit lands in the platform's clone of the app; nothing reaches the code host until `commit_changes`.

1. `sync_app`, then `app_info`: note `branch` and whether the clone is clean. A dirty clone means someone else's edits are pending — stop and say so.
2. Read before writing: `read_manifest` for `platform.toml`, `list_matrix` for the clouds and services that fit the app's `type` and `language` (each entry names its `source`).
3. Make the change: `write_manifest` with the full file, `set_cloud` with the target (and `source` for a custom repository), or `add_service` with name and provider. Several edits can precede one commit.
4. `commit_changes` with a Conventional Commit message. On `main`, `master` or `develop` pass `branch_kind` (`chore` for configuration) and `branch_code` — the changes move to `<kind>/<code>` — and `pull_request=true` to push and open the PR. On a work branch, `push=true` is enough; open the PR with the open-pull-request skill when the work is done.
5. Report the branch, the commit sha and the pull request URL. The role must allow `app.configure`; a refused call names the missing permission.
