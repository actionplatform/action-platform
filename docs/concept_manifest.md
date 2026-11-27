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

[gitflow.protection]
enforce = true
```

## Tables

| Table | Keys | Who reads it |
|---|---|---|
| `[project]` | `name`, `type` (web, library, docs, plugin, empty), `stack`, `template`, `language`, `ci` (github, gitlab, jenkins, bitbucket) | templates, CI scripts (`language` picks the setup/check commands), the web app |
| `[source_host]` | `kind` (github, gitlab, bitbucket, generic), `repo` (`owner/name`), `base_url` (self-hosted) | `init --push`, `release`, `pr` |
| `[release]` | `strategy = "semver"`, `changelog = "conventional"` | `release` |
| `[deploy]` | `target` (aws/lambda, aws/amplify, docker, …) plus target-specific keys | `deploy`, `rollback`, `diagnose`, `destroy` |
| `[[deploy.targets]]` | one table per target: `name`, `kind`, `run_by`, `stages`, `observe`, and the options below | `deploy`, `readiness`, the Deployments tab |
| `[[scopes]]` | one table per scope: `name`, `kind`, `criticality` | `scopes`, `readiness`, `deploy`, the Deployments tab |
| `[services]` | `<service> = "<provider>"`, e.g. `postgres = "aws-rds"` | `service add`, templates |
| `[components.<name>]` | `path` | `release -c <name>` — see [releases](concept_releases.md) |
| `[gitflow.protection]` | `enforce` (`true`/`false`; absent follows the organization's default), `branches` (default: whichever of `main`, `master`, `develop` exist), `checks` (status checks always required, e.g. `["jenkins/ci"]`) | the platform, which applies and keeps the rules on the code host — see [git-flow](concept_git_flow.md#enforced-on-the-code-host) |

## Deploy targets

```toml
[[deploy.targets]]
name = "app-prod"
kind = "docker"
run_by = "jenkins"
job = "team/app-prod"
image = "ghcr.io/acme/app"
stages = ["prod"]
version_parameter = "RELEASE_TAG"
```

| Key | Meaning |
|---|---|
| `name` | unique within the app; defaults to `kind` |
| `kind` | where the version goes: `aws/lambda`, `pypi`, `npm`, `docker`, `packagist`, `go`, or a kind a plugin adds |
| `run_by` | who deploys: `platform` (default), `github_actions`, `gitlab_ci`, `bitbucket_pipelines`, `manual`, or a CI server by its runner's name — `jenkins`, which `apx-jenkins` brings |
| `stages` | the scopes the target serves; empty means every one. With exactly one entry it is also the scope of every observed build |
| `observe` | `true` or `false`. `jenkins` and `manual` are observed by default (`observe = false` makes a Jenkins job dispatched); `observe = true` makes a `github_actions`, `gitlab_ci` or `bitbucket_pipelines` target observed. Refused on `run_by = "platform"` |
| `workflow` | the workflow file a dispatched or observed `github_actions` target runs |
| `job` | the Jenkins job path, `team/app` or `team/app/main` |
| `version_parameter` | the Jenkins build parameter that carries the release when the build's ref is not a release tag; required on a dispatched Jenkins target |
| `stage_parameter` | the Jenkins build parameter that carries the scope of an observed build |
| `package` | the project on `pypi`, `npm` and `packagist` (`vendor/name`) |
| `image` | the image on `docker` |
| `module` | the module path on `go` |
| `registry` | overrides the registry the scope's criticality pairs with |
| `component` | limits the target to one [component's](concept_releases.md) tags |

Observed and dispatched targets are explained in [deployments](concept_deployments.md#targets-and-executors).

## Scopes

```toml
[[scopes]]
name = "prod"
kind = "web"
criticality = "high"
```

`kind` is `web`, `job`, `worker`, `static` or `library`; `criticality` is `test`, `low`, `medium`, `high` or `critical`. No `[[scopes]]`, no deploy: `action-platform scopes` lists them. What a scope accepts is in [scopes](concept_scopes.md).

`LAST_VERSION` next to it holds the current version; `CHANGELOG.md` is generated.


## On the hosted platform

The platform keeps these tables itself (`app_config`, one row per app): every release, deploy, pull request and the app's pages read from there, and the app's Settings edits there — saving takes effect at once, no commit. The first time an app is seen, its `platform.toml` seeds the record. Between syncs the record is what counts; on every **Sync** the file in the clone is compared with the one last imported or exported and, when it changed in the repository — a target added in a pull request, say — the file replaces the record. Edit either side; the last one to change wins at the next sync. **Export to repository** writes the record back as `platform.toml` in the clone (a pending change to commit), for the CLI, the git hooks and the repository's CI, which keep reading the file. Applying a cloud overlay or adding a service still writes files into the clone, and the `[deploy]` / `[services]` they produce are copied into the record.
