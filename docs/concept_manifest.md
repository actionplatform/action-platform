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


## On the hosted platform

The platform keeps these tables itself (`app_config`, one row per app): every release, deploy, pull request and the app's pages read from there, and the Configuration tab edits there — saving takes effect at once, no commit. The first time an app is seen, its `platform.toml` seeds the record. Between syncs the record is what counts; on every **Sync** the file in the clone is compared with the one last imported or exported and, when it changed in the repository — a target added in a pull request, say — the file replaces the record. Edit either side; the last one to change wins at the next sync. **Export to repository** writes the record back as `platform.toml` in the clone (a pending change to commit), for the CLI, the git hooks and the repository's CI, which keep reading the file. Applying a cloud overlay or adding a service still writes files into the clone, and the `[deploy]` / `[services]` they produce are copied into the record.
