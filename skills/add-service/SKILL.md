---
name: add-service
description: Add an application dependency (database, storage) to a project as services/<name>/ with up and link scripts.
---

# Adding a service

1. `list_matrix` — services and their providers.
2. Pick the provider from context: `docker` for local development, `aws-rds`/`aws` when the project deploys to AWS. Ask when neither is clear.
3. `service_add` with `service` and `provider`. Re-adding the same service replaces its provider.
4. Report the path and how to use it: `./services/<name>/up` provisions, `eval "$(./services/<name>/link)"` loads the env vars the app reads.
