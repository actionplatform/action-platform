---
name: add-cloud
description: Attach or switch the deploy target of a project (aws/lambda, aws/amplify, docker) with a cloud overlay.
---

# Adding a cloud

1. `project_info` — note `type` and `language`; `list_matrix` shows which clouds accept them.
2. `cloud_set` with the cloud name. It writes deploy files and sets `[deploy] target`, replacing any previous one.
3. If the overlay refuses the project (type or language unsupported), say which clouds do fit instead of retrying blindly.
4. Files were written to the working tree, not committed. If the project is already under git-flow, this belongs on a branch (`start_branch` with kind `chore`), then a Conventional Commit such as `chore(deploy): add aws/lambda overlay`.
5. Report what was added: `DEPLOY.md` explains setup; `requirements/` holds the least-privilege IAM policy for AWS clouds.
