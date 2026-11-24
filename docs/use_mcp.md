# MCP

The platform ships as an MCP server. Claude Code, Codex, Cursor — anything that speaks MCP — gets 21 local tools (`list_matrix`, `init_project`, `install_platform`, `start_branch`, `gitflow_audit`, `propose_pull_request`, `release`, `list_scopes`, `readiness`, `deploy`, `diagnose`, …) or 69 remote ones (projects and their apps, configuration, git-flow, releases, readiness, deployments, jobs, CI, importing a GitHub organization, GitLab group or Bitbucket workspace, plus orientation, organization management and access on the organization's services), prompts that put them in the right order (local: `new_service`, `ship_feature`, `cut_release`, `deploy_project`, `adopt_repository`, `fix_gitflow`; remote: `orient`, `new_app`, `ship_change`, `cut_release`, `deploy_app`, `adopt_repository`, `adopt_organization`) and, from the plugin repository, 15 skills that make the agent preview and ask before anything leaves the machine. Every tool carries an input schema and an output schema (`action_platform/mcp/schemas.py`), and a platform error — a refused permission, an unknown app, a git-flow violation — comes back as the tool's error text, so the agent can read why.

```bash
pip install "action-platform[mcp]"
action-platform mcp                 # stdio
action-platform mcp --http          # http://127.0.0.1:8765/mcp
```

Claude Code — the plugin, its 15 skills and the Codex/Cursor manifests live in [actionplatform/action-platform-mcp](https://github.com/actionplatform/action-platform-mcp):

```bash
/plugin marketplace add actionplatform/action-platform-mcp
/plugin install action-platform@action-platform
```

Any client — add to `.mcp.json`:

```json
{ "mcpServers": { "action-platform": { "command": "uvx", "args": ["--from", "action-platform[mcp]", "action-platform-mcp"] } } }
```

## Local vs remote

```mermaid
flowchart LR
    subgraph local["action-platform mcp"]
        L1[MCP tools] --> C1[[core]] --> F[(files in cwd)]
    end
    subgraph remote["action-platform mcp --remote"]
        L2[MCP tools] -->|Bearer| V["/api/v1/* (gate: role ∩ scope ∩ reach)"] --> API[action-platform-api serve] --> WS[(workspaces)]
    end
    login["action-platform login <url>"] -.->|device flow · scoped JWT| L2
```

| | `action-platform mcp` | `action-platform mcp --remote` |
|---|---|---|
| Acts on | the current directory and files on this machine | apps on the hosted platform you logged in to |
| Tools | `list_matrix`, `init_project`, `install_platform`, `push_project`, `cloud_set`, `service_add`, `project_info`, `start_branch`, `gitflow_audit`, `install_hooks`, `propose_pull_request`, `open_pull_request`, `release`, `list_scopes`, `readiness`, `deploy`, `rollback`, `diagnose`, `job_logs`, `record_deployment`, `gitflow_rules` | `whoami`, `current_context`, `list_organizations`, `list_projects`, `list_teams`, `list_members`, `create_project`, `delete_project`, `create_team`, `add_team_member`, `remove_team_member`, `assign_project_team`, `set_member_role`, `remove_member`, `list_invitations`, `invite_member`, `cancel_invitation`, `list_apps`, `add_app`, `init_app`, `remove_app`, `sync_app`, `app_info`, `gitflow_audit`, `app_commits`, `app_branches`, `app_tags`, `app_releases`, `start_branch`, `checkout_branch`, `propose_pull_request`, `open_pull_request`, `read_manifest`, `write_manifest`, `set_cloud`, `add_service`, `commit_changes`, `release`, `deploy`, `diagnose`, `list_deployments`, `record_deployment`, `list_scopes`, `create_scope`, `update_scope`, `delete_scope`, `release_readiness`, `recheck_readiness`, `job_status`, `job_logs`, `get_app_ci`, `set_app_ci`, `run_ci`, `list_ci_hosts`, `add_ci_host`, `test_ci_host`, `list_hosts`, `set_app_host`, `list_import_organizations`, `preview_organization_import`, `import_organization`, `list_matrix`, `gitflow_rules`, `access_audit`, `access_who`, `access_grant`, `access_revoke`, `access_offboard`, `access_sync` |
| Templates | official repository, or another one with `source=url[@ref]` | official plus every repository the organization added under Templates; custom entries are addressed by `source=<name>` |
| Permissions | whatever your user can do | your role in the organization (`viewer`, `developer`, `deployer`, `admin`, `owner`) narrowed by the token's scope (`read`, `write`, `release`, `admin`) and reach (one organization or all, optionally one project or app); a refused call names the missing permission or scope |
| Credentials | your environment | the JWT from `action-platform login` (everything your role allows by default; `--scope read` for a read-only assistant, `--scope read,write,release` for one that ships but cannot manage the organization), sent as `Authorization: Bearer` to `/api/v1/*` (the web app forwards the path to the API, whose gate applies the rules); the server also sends the MCP client's name (`clientInfo`) so *Connected apps* can show Claude Code, Codex or Cursor next to the token |

`list_deployments` answers with the app's targets and what arrived at each, whoever shipped it (`sync=true` asks the observed pipelines first); the remote `deploy` runs on the request unless `background=true`, which queues it on the worker like the web does (a dispatched Jenkins target records each scope the build covers) and answers with a job id that `job_logs` (`after=next` until `finished`) and `job_status` follow; `release_readiness` returns the checks the release page shows per scope — a `blocked` verdict makes `deploy` refuse that scope — and `recheck_readiness` queues a new check; `record_deployment` writes down a delivery made outside the platform — a release, always. Both default `release` and `deploy` to dry runs; the tool descriptions tell the agent to show the result and ask before calling again with `dry_run=false`. `release` accepts `branch`: stable versions come only from `main`/`master`, any other branch yields `X.Y.Z-rc.N`.

On the local server `list_scopes` reads `[[scopes]]` of `platform.toml`, and `readiness` runs the same checks as `action-platform readiness` for a release and a scope (configuration, manifests, credentials, permissions, the destination's state; nothing built or changed) and answers with a `verdict` and every check's id, severity, detail and fix, so the agent sees a blocked release before the dry run. `job_logs` and `record_deployment` reach the platform the CLI is logged in to (`action-platform login`): the log of a job it ran, and a delivery made outside it, for the app whose name the checkout's `platform.toml` carries unless `app` says otherwise. The `cloud` and `service` parameters of `init_project`, `cloud_set` and `service_add` list what this machine's templates and enabled plugins offer (a plugin's cloud such as `dokploy` included); `list_matrix` describes each.

`init_project` takes `owner` (default: the account of this machine's host credentials), `author` (default `git config user.name`), `license` (`mit`, `apache-2.0` or `none`, the default — no `LICENSE`) and `host`, and answers which owner, author and licence it used. `push_project` creates a private repository unless `private=false`, and refuses a project whose `platform.toml` names no owner. `init_app` on the remote server takes `license` and `private` (default true) the same way; the author is the organization's commit identity when it set one.

Apps live in projects: `add_app` and `init_app` take a `project` (id or slug from `list_projects`) and answer with `registry_id`, the id every other app tool takes; `remove_app` and `delete_project` leave the repositories on the code host unless `repository` / `repositories` is true — irreversible, so the rules below make the agent ask first.

## Rules the server states

Both servers hand the client the same rules in their instructions, and the skills repeat them:

- git-flow always — no commits on `main`, `master` or `develop`; every change on a `<kind>/<code>[-slug]` branch from `start_branch`; a pull request only after `gitflow_audit` passes and the user approved the `propose_pull_request` preview; Conventional Commits, one commit per concern;
- the platform is reached only through the tools — never its HTTP API, the web app or the code host's API directly (no `curl`, `fetch`, `gh api`, hand-written requests), never its tokens, never `git push` / `gh pr create` / a deploy command to bypass a tool: the tools carry the role, the scope and the audit trail;
- anything that leaves the machine — push, pull request, release, deploy, rollback, removing an app or a project, deleting a repository — is shown first and waits for an explicit yes; dry runs first;
- a refusal is reported with its reason and the agent stops; it does not look for a way around the permission.

Orientation tools on the remote server: `whoami` (account, organization, role, token scope and reach, resulting permissions), `current_context` (matches the local checkout's git remote to a platform app and says what the token may do there), `list_organizations` (every organization with your role and the scopes a token could get), `list_projects` (projects, teams and apps within the token's reach), `list_teams`, `list_members`. When the token spans every organization these take an `organization` argument (id or slug); `list_apps` and `list_projects` answer across all of them without it. An agent asked "what can I do here?" answers from these without guessing. Management tools — `create_project`, `create_team`, `add_team_member`, `remove_team_member`, `assign_project_team`, `set_member_role`, `remove_member`, `list_invitations`, `invite_member`, `cancel_invitation` — need the matching role (`project.manage` / `org.manage`) and an `admin`-scoped token that is not limited to a project or app; only an owner removes an owner or gives the owner role. `invite_member` sends no email: it answers with the invitation's `link`, which the person opens to sign in or sign up with the invited email.

Access tools — `access_audit`, `access_who`, `access_grant`, `access_revoke`, `access_offboard`, `access_sync` — keep the organization's members, roles and teams in line with who has access on the services its plugins own ([service access](concept_service_access.md)). They need `org.manage` and an `admin`-scoped token; every change is a dry run until `apply` is true. They exist only on the remote server: the credentials of each service stay sealed on the platform.

Adopting what already exists, on the remote server: `list_import_organizations` and `preview_organization_import` show a GitHub organization's, GitLab group's or Bitbucket workspace's repositories, projects, teams and people, with what the host cannot provide; `import_organization` brings the picked ones in as a job (`job_status` has its summary); `list_ci_hosts`, `add_ci_host` (the token is read from an environment variable the user names on the machine running the server, never typed into the chat) and `test_ci_host` manage Jenkins servers (`org.manage`); `set_app_ci` points an app at the job that already builds it, `get_app_ci` (`sync=true` asks for new runs) and `run_ci` read and start it; `list_hosts` and `set_app_host` choose which code host an app's clone uses. Each tool calls the same `/api/v1` route as the web, so the role and the token's scope are checked there.

Remote editing follows the same loop as the web app: `write_manifest` / `set_cloud` / `add_service` change the workspace (the workspace), `commit_changes` commits — on a new `<kind>/<code>` branch with `branch_kind` + `branch_code` when the clone sits on a protected branch — and, with `pull_request=true`, pushes and opens the PR in one call. The web app's `/api/v1` proxy injects the organization's code-host credentials, so private repositories, pushes and pull requests work without any token on the client.

Point Claude Code at a hosted platform:

```json
{ "mcpServers": { "platform": { "command": "action-platform", "args": ["mcp", "--remote"] } } }
```
