---
name: scaffold-project
description: Create a new project from the templates matrix — pick type, stack and template from list_matrix, generate locally, never push.
---

# Scaffolding a project

Local only. Pushing and clouds are separate skills.

1. `list_matrix`. Never guess a type, stack or template name. When the user names another templates repository, pass it as `source` (`url[@ref]` locally; the source's name on a hosted platform) and keep the same value on every later call.
2. Map the request to a leaf: an HTTP API or MCP server is `web`; a package is `library`; a docs site is `docs`; a browser extension is `plugin`; "just the config" is `empty`.
3. When the stack has one template, omit `template` — the default is used. When there are several, ask which unless the user named one.
4. `init_project` (hosted: `init_app`) with `type`, `stack`, `name`, `ci` (`github` unless told) and the same `source` if one was used. Leave `cloud` empty here; use the add-cloud skill if a target was named.
5. Report the path and `project_info`. Mention that nothing was pushed.
6. Once the repository is initialized (push-project skill does it), the CLI installs git hooks into `.git/hooks` and git-flow is enforced locally. Further work goes through the start-branch skill.
