---
name: push-project
description: Create the remote repository for a generated project and push it — only after the user confirms owner, name and visibility.
---

# Pushing a project

`push_project` creates a repository other people can see. It is never implicit.

1. `project_info` — read `name` and `github_owner`. The repository will be `<github_owner>/<name>`.
2. Say exactly that: owner, name, public or private. Ask for a yes.
3. On yes, `push_project` with `private` as agreed. Report the remote URL.
4. Deploy workflows in the repo skip themselves until `AWS_DEPLOY_ROLE_ARN` (and `AMPLIFY_APP_ID` for Amplify) exist as GitHub environment secrets; point the user to `DEPLOY.md` and `requirements/` for the IAM role.

Never call `push_project` in the same turn as `init_project` without an explicit yes.
