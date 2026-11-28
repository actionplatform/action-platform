# Glossary

One line per term. [Core concepts](start_concepts.md) explains how the main ones relate.

| Term | Means |
|---|---|
| organization › project › app | the hierarchy; an app is one git repository |
| team | a group of organization members that looks after projects; a project belongs to at most one |
| member · invitation | a person in an organization with a role; everyone after the first account joins by invitation |
| role · permission | `owner`, `admin`, `deployer`, `developer`, `viewer`; the six permissions a role grants in an organization (`org.manage`, `project.manage`, `app.release`, `app.configure`, `app.flow`, `app.sync`) |
| token · scope · reach | what `action-platform login` mints; what it may do (`read`, `write`, `release`, `admin`); where it may act (organizations, a project, an app) |
| source host | GitHub, GitLab, Bitbucket or a generic git remote, connected per organization under Connect → Git |
| webhook | the host's notification of pushes, pull requests, releases and pipeline runs; it syncs the app within seconds |
| workspace | the platform's disposable clone of an app, rebuilt from the remote whenever a request needs its files |
| sync | fetching the remote and importing releases, pull requests and pipeline runs |
| pending changes | changes the platform holds for an app, written onto the clone until **Commit changes** or **Discard changes** |
| manifest | `platform.toml`, the file that declares a project: type, language, git-flow rules, deploy targets, scopes |
| `LAST_VERSION` | the file with the current version of a repository or component; `release` bumps it |
| component | a part of a repository released on its own, with its own path, version and tag prefix (`api/v1.2.3`) |
| template · overlay | a project skeleton (type › stack › template); an overlay adds a cloud (`aws/lambda`, `dokploy`, `docker`) or a service on top of it |
| template source | a repository of templates; the official one plus any the organization adds |
| service | an infrastructure dependency added to an app as an overlay, such as `postgres` |
| service access | what members may do on the tools the team uses, kept in line with their platform roles |
| git-flow | the branch kinds, the base each starts from, the target each merges into, the Conventional Commit format the hooks and CI enforce |
| branch protection | the git-flow rules set on the code host itself (`[gitflow.protection]`) |
| release | a version cut from a repository or component: tag, changelog, release on the host |
| release shape | `candidate` (`X.Y.Z-rc.N`), `stable` (cut on `main`/`master`) or `hotfix` (cut on `hotfix/*`) |
| scope | a named destination of an app with a kind and a criticality; no scope, no deploy |
| criticality | `test`, `low`, `medium`, `high`, `critical`; decides which release shapes a scope accepts |
| stage | the name a deploy target receives for a scope; the same as the scope's name |
| deploy target | where a release goes (`kind`: `aws/lambda`, `dokploy`, `pypi`, `docker`…) and who runs it (`run_by`), declared under `[deploy]` or `[[deploy.targets]]` |
| executor | who runs a deploy: `platform`, `github_actions`, `gitlab_ci`, `bitbucket_pipelines`, `jenkins` or `manual` |
| dispatched · observed | a target the platform starts on a release tag, or one whose runs the platform only records |
| deployment | one release arriving at one scope through one target; `queued`, `running`, `success`, `failure`, `verified` |
| verified | the platform found that exact version at the destination |
| readiness | whether a release can reach a scope, checked per scope after every release without building; a blocked release refuses the deploy unless forced |
| preflight | a deploy's checks without the deploy (`dry_run`) |
| job | queued work the worker runs: sync, release, readiness, deploy, destroy, import |
| worker | the process that claims and runs jobs; deploys run on a separate deploy worker |
| plugin · option | a Python package that adds targets, overlays, checks, tools and access providers; an option is a setting it declares, filled per organization |
| connected account | an AWS account with the plugin's IAM-only stack: an OIDC provider for the platform, a boundary and one deploy role scoped per app by a session tag |
| identity token | the short-lived JWT the platform signs about an app for a deploy; what the cloud trusts instead of a key |
| setup token | the value that proves you run the instance when creating its first account |
| MCP | Model Context Protocol; the server that exposes the platform's operations as tools for AI agents |

## Changelogs

What changed in each release: [library and CLI](../CHANGELOG.md) · [web](../apps/web/CHANGELOG.md) · [API](../apps/api/app/CHANGELOG.md).
