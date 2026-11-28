# Adopting existing repositories

For an organization that already has repositories, tags and pipelines — releases cut by hand or by CI, deploys run by Jenkins or by GitHub Actions — and wants the platform to record, verify and gate them without moving them. Nothing here asks you to re-cut a release or to hand a deploy over: the platform can watch a pipeline that keeps running as it is ([deployments](concept_deployments.md)).

Order: bring the repositories in, install the files, describe where releases land, connect the CI, check.

## Many repositories or one

**Many, from a GitHub organization, GitLab group or Bitbucket workspace.** *Import* (Projects → **Import**, an admin) reads it through a connected code host, lists what the token sees and queues one job that creates the projects and apps. Over the API:

```bash
GET  /api/v1/import/<host id>/organizations
GET  /api/v1/import/<host id>/organizations/acme      # the preview
POST /api/v1/import
{
  "host_id": "<host id>",
  "organization": "acme",
  "repositories": ["acme/api", "acme/web"],
  "project_id": "<existing project id>"
}
```

`repositories` are full names as the host shows them (`owner/name`; `group/subgroup/name` on GitLab). Without `project_id` each repository becomes its own project; with it, all of them become apps of that project. The answer is `202` with a job id and a `poll` path (`/api/v1/jobs/<id>`); the job ends with what it created and what it skipped, with the reason. Repositories already on the platform are skipped. The same body takes `projects`, `teams`, `people`, `role`, `roles` and `people_roles` to bring the host's projects, teams and members along — see [web](use_web.md#import). The GitHub-only paths (`/api/v1/import/github/organizations?host=`, `POST /api/v1/import/github`) still answer, for any host.

An imported app is registered as it is: its files are not touched. The releases and pull requests already on the code host are imported with it, so the Releases tab starts with your existing tags and there is nothing to re-cut.

**One.** *Add an existing repository* on a project (`POST /api/v1/projects/{id}/apps {url, install}`, the `add_app` tool) with its URL. It installs the platform files when they are missing and leaves them as pending changes; **Commit changes** opens the pull request.

Either way, install the files next: per repository below, or for many apps of a project at once from the project's **Adoption** page (`POST /api/v1/projects/{id}/install`), which previews each plan and then opens one pull request per repository — see [web](use_web.md#adoption) and [API](use_api.md#adoption).

## Install on an existing repository

```bash
cd acme-api
action-platform install --dry-run     # what would be created
action-platform install
```

`install` adds what is missing and keeps what exists: `platform.toml`, `LAST_VERSION`, `AGENTS.md`, `.code_quality/`, the CI files and the git hooks. A file the repository already has is listed as `exists, kept`; the CLI prints `+` for each created file and `=` for each kept one.

**Which CI.** The first that applies:

1. `--ci github|gitlab|jenkins|bitbucket|none`;
2. `[project] ci` of an existing `platform.toml`;
3. the CI the files show: `Jenkinsfile`, `.gitlab-ci.yml`, `bitbucket-pipelines.yml`, any `.github/workflows/*.yml`;
4. the remote's host: GitLab CI for a GitLab remote, Bitbucket Pipelines for a Bitbucket one, otherwise GitHub Actions.

A repository that shows more than one CI and no `--ci` is refused, naming them: pass the one the platform's checks belong to, or `none`. `--ci` naming a CI other than the one present is applied with a warning (`Jenkinsfile found; installing github CI files runs a second CI next to it`). **`--ci none`** writes no pipeline files at all — the right choice when the pipelines are yours and stay untouched.

With **Jenkins** and a `Jenkinsfile` already there, the file is kept and `install` prints the stages that run the platform's checks from [ci-jenkins](https://github.com/actionplatform/ci-jenkins) — `apSetup`/`apCheck`, and `apConventionalCommit` and `apGitflow` on pull requests — with the `library` line to put at its top; paste them into the pipeline's `stages`. The MCP tool `install_platform` returns them as `ci_snippet`, next to `detected_ci` and `warnings`; the web shows them after installing.

**Type and language.** `--type web|library|docs|plugin` (default `web`) goes into `platform.toml`. The language is detected; `--language python|go|node|php|java|rust|ruby` sets it, and **`--language none`** installs no `.code_quality/` and no code-quality workflow.

**`LAST_VERSION`** is seeded from the tags: the highest release tag among all the repository's tags, `v1.2.3` or `1.2.3`, from any branch. A pre-release is the seed only while no stable release follows it (`v1.9.0` and `v2.0.0-rc.1` give `2.0.0-rc.1`; once `v2.0.0` exists, `2.0.0`). Tags that are not versions are ignored. Without a release tag, the version the manifest declares — `pyproject.toml`, `package.json`, `Cargo.toml`, `composer.json`, `pom.xml`, the files `release` rewrites — else the newest `CHANGELOG.md` heading (`## [3.4.2]`, `## v3.4.2`); `0.0.0` when there is none. When a tag and the manifest disagree, the higher wins and the plan warns. An existing `platform.toml` with `[components]` gets a `LAST_VERSION` under each component's `path`, seeded from its `<name>/vX.Y.Z` tags, manifest or CHANGELOG the same way. `--version X.Y.Z` sets the root's seed. The plan names each seed and where it came from (`+ LAST_VERSION 3.4.2 from pyproject.toml`), and warns when an existing `CHANGELOG.md` uses another format than the `## vX.Y.Z — date` entries `release` adds above it. The first `action-platform release` continues from there.

**Git hooks** go into `.git/hooks` of that clone only — they are not versioned, and each person who wants them runs `install` in their own clone. A hook you already had is kept as `<name>.pre-action-platform` and still runs after ours. They refuse a branch that is not `<kind>/<code>[-slug]` (outside `main`, `master`, `develop`), a commit message that is not a Conventional Commit, and any commit or push of a commit to `main`, `master` or `develop` unless its message starts with `chore(release):` or `chore(platform):`. **A team that commits straight to its default branch should not install the hooks there**: skip `install`, or run it on a clone and remove the hooks (`rm .git/hooks/{pre-commit,commit-msg,pre-push,gitflow.sh}`), and adopt git-flow when the team is ready. The platform itself, the recording and the readiness checks do not need the hooks.

Review the files, then commit them with the message the command suggests (`chore(platform): install action-platform`).

## Releases you already have

Tags and releases on the code host are imported by **Sync** and by the host's webhook; they appear in the Releases tab as they are. A deployment must reference one of them — the tag `vX.Y.Z`, or `<component>/vX.Y.Z` for a [component](concept_releases.md) — so a pipeline that deploys from a branch with no release is a CI run, not a deployment, and is not recorded as one (unless it receives the release as a parameter, below). An existing `CHANGELOG.md` is kept; `release` prepends its entry to it.

## Scopes: where a release lands

A [scope](concept_scopes.md) is one place a release lands, with a kind and a criticality. Make one per place, not per pipeline:

```toml
[[scopes]]
name = "dev"
kind = "web"
criticality = "test"

[[scopes]]
name = "prod-eu"
kind = "web"
criticality = "critical"

[[scopes]]
name = "prod-eu-worker"
kind = "worker"
criticality = "critical"
```

The same list is on the app's **Scopes** tab, `POST …/apps/{id}/scopes` and the `create_scope` tool; `action-platform scopes` prints the file's. `kind` is `web`, `job`, `worker`, `static` or `library`; `criticality` is `test` to `critical` and decides which releases the scope takes (candidates only reach `test` and `low`).

Several targets may observe the same pipeline job. A job that deploys two places is two targets, each with a single-entry `stages` — one build then yields one deployment per target, each on its own scope. Parts shipped together by one deploy, such as the functions of one stack, can each be a scope observed from the same job.

## Targets that observe

A target says where a version goes (`kind`) and who puts it there (`run_by`). For a pipeline you keep, the platform only reads:

**Jenkins** is observed by default. The platform reads the builds of `job` and turns each one that shipped a release into a deployment:

```toml
[[deploy.targets]]
name = "api-prod"
kind = "docker"
run_by = "jenkins"
job = "team/api-prod"
image = "ghcr.io/acme/api"
stages = ["prod-eu"]
version_parameter = "RELEASE_TAG"

[[deploy.targets]]
name = "api"
kind = "docker"
run_by = "jenkins"
job = "team/api"
image = "ghcr.io/acme/api"
version_parameter = "RELEASE_TAG"
stage_parameter = "ENV"
```

- the release is the tag the build checked out; when the build's ref is not a release tag, it is the value of `version_parameter` (`v1.2.3`, `1.2.3` or `<component>/v1.2.3`); a build with neither is not recorded;
- the scope is the value of `stage_parameter`; otherwise the target's `stages`, when it has exactly one entry (one job per environment); otherwise none.

**GitHub Actions, GitLab CI, Bitbucket Pipelines** are dispatched by default. For a workflow that keeps deploying on its own, add `observe = true`: its runs on a release tag are imported on **Sync** and verified, and a platform deploy never starts it.

```toml
[[deploy.targets]]
name = "pypi"
kind = "pypi"
run_by = "github_actions"
workflow = "publish.yml"
package = "acme-api"
observe = true
```

**Manual**: `run_by = "manual"` for something a person does. After doing it, write it down:

```bash
action-platform deploy-record api-prod 1.4.0 --scope prod-eu --url https://api.example.com
action-platform deploy-record api-prod 1.3.9 --scope prod-eu --failed
```

`--app` names the app when the command does not run inside its repository. It needs `action-platform login`. `POST /api/v1/projects/{p}/apps/{a}/deployments` and the `record_deployment` tool do the same; use them to backfill what each scope runs today so Deployments starts truthful.

What the platform does with an observed target:

- **Deploy.** A deploy whose only matching targets are observed is refused, naming the executor: `api-prod is deployed by jenkins; the platform records it, it does not run it`.
- **Readiness.** The target is listed as `api-prod (observed, jenkins)` and passes, so an app deployed only by Jenkins is not blocked for lacking a target the platform runs. Its own checks run when its kind has a provider, and every one is a warning, never a block.
- **History.** Each run becomes a deployment on **Sync** (`action-platform deployments --sync`), linked to the CI run, and is verified at the destination when the kind can answer.

A Jenkins job the platform should also be able to start is a dispatched target (`observe = false`): see [dispatched Jenkins jobs](concept_deployments.md#dispatched-jenkins-jobs).

## Connect Jenkins

1. Connect → **CI** → Servers → add a server: name, base URL, username and API token (Jenkins → your user → Security → API Token), or `POST /api/v1/ci-hosts {kind: "jenkins", name, base_url, username, token}`. *Test* (`POST /api/v1/ci-hosts/{id}/test`) reaches it with the sealed token.
2. On the app's **Settings › CI** choose the server and the job path as Jenkins shows it in the URL (`team/api`, or `team/api/main` for a multibranch branch), or `PUT /api/v1/projects/{p}/apps/{a}/ci {"ci_host_id": "<id>", "job": "team/api"}`. **Sync** (`POST …/ci/sync`) imports the runs.
3. Put the same job path in the target's `job`, then **Sync** the app's deployments.

The Jenkins account needs only read on the jobs it observes: *Overall/Read* and *Job/Read* on their folders. A `404` from Jenkins on a job that exists usually means the account cannot see that folder — Jenkins answers not found where it would otherwise say forbidden — so grant it read on the folder rather than checking the path first. Starting a job needs more, only for dispatched targets ([web](use_web.md#ci)).

For GitHub Actions, GitLab CI and Bitbucket Pipelines nothing is connected here: the app's source host token is used.

## Verified at the destination

A green pipeline says the job finished, not that the version arrived. These kinds ask the destination themselves, on Sync and after a run, and mark the deployment `verified` when the version is there:

| Kind | Option | Asks |
|---|---|---|
| `pypi` | `package` | PyPI for the version of the package |
| `npm` | `package` | the npm registry |
| `docker` | `image` | the registry for the tag's manifest |
| `packagist` | `package` (`vendor/name`) | the package's versions on Packagist, with or without the `v` |
| `go` | `module` | the Go module proxy for `v<version>` |

For an observed target a version already at the destination is the expected state, so readiness reports it as passing.

## Checklist

- [ ] Repositories imported (`POST /api/v1/import`) or added one by one; their releases appear in the Releases tab.
- [ ] `action-platform install --dry-run` (or the Adoption preview) read; `--ci`, `--type` and `--language` chosen on purpose, `--ci none` where the pipelines stay yours.
- [ ] `LAST_VERSION` equals the newest release tag.
- [ ] Hooks installed only where the team works through branches and pull requests.
- [ ] One scope per place a release lands, with kind and criticality.
- [ ] A `[[deploy.targets]]` per place a pipeline deploys, with `run_by`, `job` or `workflow`, `stages` and, for Jenkins, `version_parameter` and, when the job serves several scopes, `stage_parameter`.
- [ ] Jenkins connected, the account able to read every observed folder, the app's CI linked.
- [ ] What each scope runs today recorded with `deploy-record`.
- [ ] `action-platform deployments --sync` lists the targets and their latest versions; `action-platform readiness --version X.Y.Z --scope <scope>` shows the observed targets as warnings at most.

Related: [deploy from the web](guide_first_deploy.md) · [deployments](concept_deployments.md) · [scopes](concept_scopes.md) · [manifest](concept_manifest.md) · [git-flow](concept_git_flow.md) · [troubleshooting](start_troubleshooting.md).
