# `platform.toml`

Everything a project needs is declared in one file:

```toml
[project]
name = "orders"
type = "web"
stack = "python"
template = "fastapi"
ci = "github"
language = "python"

[source_host]
kind = "github"
repo = "acme/orders"

[deploy]
target = "aws/lambda"

[services]
postgres = "aws-rds"
```

## Tables

| Table | Keys | Who reads it |
|---|---|---|
| `[project]` | `name`, `type` (web, library, docs, plugin, empty), `stack`, `template`, `language`, `ci` (github, gitlab, jenkins, bitbucket) | templates, CI scripts (`language` picks the setup/check commands), the web app |
| `[source_host]` | `kind` (github, gitlab, bitbucket, generic), `repo` (`owner/name`), `base_url` (self-hosted) | `init --push`, `release`, `pr` |
| `[release]` | `strategy = "semver"`, `changelog = "conventional"` | `release` |
| `[deploy]` | `target` (aws/lambda, aws/amplify, docker, …) plus target-specific keys | `deploy`, `rollback`, `diagnose`, `destroy` |
| `[services]` | `<service> = "<provider>"`, e.g. `postgres = "aws-rds"` | `service add`, templates |
| `[components.<name>]` | `path` | `release -c <name>` — see [releases](concept_releases.md) |

`LAST_VERSION` next to it holds the current version; `CHANGELOG.md` is generated.

Read and edited by `action_platform/core/manifest`.
