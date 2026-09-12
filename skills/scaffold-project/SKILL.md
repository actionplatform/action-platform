---
name: scaffold-project
description: Create a new project from the templates matrix — pick type, stack and template from list_matrix, generate locally, never push.
---

# Scaffolding a project

Local only. Pushing and clouds are separate skills.

1. `list_matrix`. Never guess a type, stack or template name.
2. Map the request to a leaf: an HTTP API or MCP server is `web`; a package is `library`; a docs site is `docs`; a browser extension is `plugin`; "just the config" is `empty`.
3. When the stack has one template, omit `template` — the default is used. When there are several, ask which unless the user named one.
4. `init_project` with `type`, `stack`, `name`, `ci` (`github` unless told). Leave `cloud` empty here; use the add-cloud skill if a target was named.
5. Report the path and `project_info`. Mention that nothing was pushed.
