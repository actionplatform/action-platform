"""Tools that act on a hosted platform through `action-platform login`, not on the local checkout."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Optional

from pydantic import Field

from action_platform.mcp import schemas
from action_platform.mcp.annotations import DESTRUCTIVE, READ_ONLY, REACHES_OUT, tool
from action_platform.core.exception import ActionPlatformError
from action_platform.core.flow.repository import Repository
from action_platform.remote.client import Remote

AppId = Annotated[str, Field(description="App id from list_apps")]
ProjectId = Annotated[
    str,
    Field(description="Project id or slug from list_projects; apps live in projects"),
]
OrgId = Annotated[
    Optional[str],
    Field(
        description="Organization id or slug; needed only when the token spans every organization (see whoami)"
    ),
]


def _repo_key(url: str) -> str:
    """owner/name of a git URL, so https://github.com/a/b.git and git@github.com:a/b match."""
    text = url.strip().removesuffix(".git").rstrip("/")
    text = text.replace(":", "/")
    parts = [p for p in text.split("/") if p]

    return "/".join(parts[-2:]).lower() if len(parts) >= 2 else ""


def _org_of(row: dict) -> Optional[str]:
    """The organization a project row names when the token spans every organization; None when it does not need saying."""
    organization = row.get("organization") or {}

    return organization.get("id") if isinstance(organization, dict) else None


def _project_of(
    remote: Remote, project: str, organization: Optional[str] = None
) -> dict:
    """The project row for an id or slug; a name the platform does not know is an error the agent can read."""
    for row in remote.projects(organization=organization):
        if project in (row.get("id"), row.get("slug")):
            return row

    raise ActionPlatformError(f"no project {project!r}: list_projects shows them")


def _app_in_project(remote: Remote, app_id: str) -> tuple[dict, dict]:
    """(project, app) for an app id from list_apps, which is the registry id the workspace tools use."""
    for project in remote.projects():
        for app in project.get("apps") or []:
            if app_id in (app.get("registry_id"), app.get("id")):
                return project, app

    raise ActionPlatformError(f"no app {app_id!r}: list_apps shows them")


def register(mcp: Any, remote: Remote) -> None:
    @tool(mcp, annotations=READ_ONLY)
    def whoami() -> schemas.WhoAmI:
        """Who these tools act as and what they may do: account, organization, role, the token's scope and reach (project/app), and the permissions that result — call first when unsure whether an action is allowed."""
        who = remote.whoami()

        return {
            "server": remote.server,
            "user": who.get("user"),
            "organization": who.get("organization"),
            "organizations": who.get("organizations"),
            "spans_every_organization": who.get("organization") is None,
            "role": who.get("role_label") or who.get("role"),
            "scope": who.get("scope"),
            "limited_to": {"project": who.get("project"), "app": who.get("app")},
            "can": {k: v for k, v in (who.get("permissions") or {}).items()},
        }

    @tool(mcp, annotations=READ_ONLY)
    def list_organizations() -> list[schemas.OrganizationRow]:
        """Every organization the account belongs to, with the role there and what a token could be granted. The current token acts on one organization only (see whoami)."""
        return remote.organizations()

    @tool(mcp, annotations=READ_ONLY)
    def list_projects(organization: OrgId = None) -> list[schemas.ProjectRow]:
        """Projects with their team and apps; limited to the token's project or app when it has one. A token that spans every organization lists them all (each with its organization) unless `organization` narrows it."""
        return remote.projects(organization=organization)

    @tool(mcp, annotations=READ_ONLY)
    def list_teams(organization: OrgId = None) -> list[schemas.TeamRow]:
        """Teams in the organization: members and the projects each team owns."""
        return remote.teams(organization=organization)

    @tool(mcp, annotations=READ_ONLY)
    def list_members(organization: OrgId = None) -> list[schemas.MemberRow]:
        """Members of the organization and their roles."""
        return remote.members(organization=organization)

    @tool(mcp, annotations=REACHES_OUT)
    def create_project(
        name: str,
        description: Annotated[str, Field(description="Optional description")] = "",
        organization: OrgId = None,
    ) -> schemas.Created:
        """Create a project in the organization (needs project.manage and an admin-scoped token)."""
        return remote.create_project(name, description, organization=organization)

    @tool(mcp, annotations=REACHES_OUT)
    def create_team(
        name: str,
        description: Annotated[str, Field(description="Optional description")] = "",
        organization: OrgId = None,
    ) -> schemas.Created:
        """Create a team in the organization (needs org.manage and an admin-scoped token)."""
        return remote.create_team(name, description, organization=organization)

    @tool(mcp, annotations=REACHES_OUT)
    def add_team_member(
        team_id: Annotated[str, Field(description="Team id from list_teams")],
        user_id: Annotated[str, Field(description="User id from list_members")],
        organization: OrgId = None,
    ) -> schemas.Ok:
        """Put an organization member on a team (needs org.manage)."""
        return remote.add_team_member(team_id, user_id, organization=organization)

    @tool(mcp, annotations=REACHES_OUT)
    def assign_project_team(
        project_id: Annotated[str, Field(description="Project id from list_projects")],
        team_id: Annotated[
            Optional[str], Field(description="Team id from list_teams; null unassigns")
        ] = None,
        organization: OrgId = None,
    ) -> schemas.Ok:
        """Give a project to a team, or take it away with team_id=null (needs project.manage)."""
        return remote.assign_project_team(
            project_id, team_id, organization=organization
        )

    @tool(mcp, annotations=REACHES_OUT)
    def set_member_role(
        user_id: Annotated[str, Field(description="User id from list_members")],
        role: Annotated[
            str, Field(description="owner, admin, deployer, developer or viewer")
        ],
        organization: OrgId = None,
    ) -> schemas.Ok:
        """Change a member's role in the organization (needs org.manage; the last owner cannot be demoted)."""
        return remote.set_member_role(user_id, role, organization=organization)

    @tool(mcp, annotations=READ_ONLY)
    def current_context(
        project: Annotated[
            Optional[str],
            Field(description="Local directory to recognise; default is the cwd"),
        ] = None,
    ) -> schemas.CurrentContext:
        """Recognise the local checkout the agent is working in: matches its git remote to an app on the platform and returns the app, its project, the organization and what the token may do there. Use before acting on "this project"."""
        root = Path(project).resolve() if project else Path.cwd()
        repo = Repository(root)
        remote_url = repo.remote_url() if repo.exists() else ""
        key = _repo_key(remote_url)
        who = remote.whoami()
        match = next(
            (a for a in remote.apps() if key and _repo_key(a.get("url") or "") == key),
            None,
        )
        projects = remote.projects() if match else []
        owner = (
            next(
                (
                    p
                    for p in projects
                    for a in p["apps"]
                    if a["registry_id"] == match["id"]
                ),
                None,
            )
            if match
            else None
        )

        return {
            "directory": str(root),
            "remote": remote_url or None,
            "branch": repo.branch if repo.exists() else None,
            "organization": who.get("organization"),
            "project": {
                "id": owner["id"],
                "name": owner["name"],
                "team": owner.get("team"),
            }
            if owner
            else None,
            "app": match,
            "role": who.get("role_label") or who.get("role"),
            "scope": who.get("scope"),
            "can": who.get("permissions"),
            "hint": None
            if match
            else "this directory is not an app on the platform — add_app registers it",
        }

    @tool(mcp, annotations=READ_ONLY)
    def list_apps(organization: OrgId = None) -> list[schemas.AppRow]:
        """Apps the platform manages — one git repository each: id, name, url, branch, version. A token that spans every organization lists them all unless `organization` narrows it."""
        return remote.apps(organization=organization)

    @tool(mcp, annotations=REACHES_OUT)
    def add_app(
        project: ProjectId,
        url: Annotated[str, Field(description="Git url; the platform clones it")],
        install_type: Annotated[
            Optional[str],
            Field(
                description="web, library, docs, plugin or empty: install the platform (platform.toml, code quality, CI, hooks) when the repository has none"
            ),
        ] = None,
        install_ci: Annotated[
            Optional[str],
            Field(
                description="github, gitlab, jenkins, bitbucket, or none for no pipeline files; default from the remote"
            ),
        ] = None,
    ) -> schemas.AppAdded:
        """Register a repository as an app inside a project on the platform.

        A repository without platform.toml is refused with code `needs_install`;
        call again with install_type to have the platform files added to the
        clone, then commit them with commit_changes (branch + pull request).
        The answer carries `registry_id`: the id the other app tools take.
        """
        install = {"type": install_type, "ci": install_ci} if install_type else None
        row = _project_of(remote, project)

        return remote.add_app(row["id"], url, install, _org_of(row))

    @tool(mcp, annotations=DESTRUCTIVE)
    def remove_app(
        id: AppId,
        repository: Annotated[
            bool,
            Field(
                description="Also delete the repository on the code host — irreversible; only with an explicit yes from the user"
            ),
        ] = False,
    ) -> schemas.Removed:
        """Remove an app from its project and drop the platform's clone. The repository on the code host stays unless `repository` is true."""
        project, app = _app_in_project(remote, id)

        return remote.remove_app(project["id"], app["id"], repository, _org_of(project))

    @tool(mcp, annotations=DESTRUCTIVE)
    def delete_project(
        project: ProjectId,
        repositories: Annotated[
            bool,
            Field(
                description="Also delete every app's repository on the code host — irreversible; only with an explicit yes from the user"
            ),
        ] = False,
    ) -> schemas.Removed:
        """Delete a project and remove its apps from the platform. Repositories on the code host stay unless `repositories` is true."""
        row = _project_of(remote, project)

        return remote.delete_project(row["id"], repositories, _org_of(row))

    @tool(mcp, annotations=REACHES_OUT)
    def sync_app(id: AppId) -> schemas.AppEntry:
        """git fetch + fast-forward the platform's clone. Run before auditing or releasing."""
        return remote.sync_app(id)

    @tool(mcp, annotations=READ_ONLY)
    def app_info(id: AppId) -> schemas.AppDetail:
        """platform.toml, current branch, latest tag and whether the clone is clean."""
        return remote.app(id)

    @tool(mcp, annotations=READ_ONLY)
    def gitflow_audit(id: AppId) -> schemas.GitflowReport:
        """Check the app's current branch and commits against git-flow and Conventional Commits."""
        return remote.gitflow(id)

    @tool(mcp, annotations=READ_ONLY)
    def app_commits(id: AppId, limit: int = 20) -> list[schemas.Commit]:
        """Recent commits: sha, subject, author, date."""
        return remote.commits(id, limit)

    @tool(mcp, annotations=READ_ONLY)
    def app_branches(id: AppId) -> list[schemas.BranchRow]:
        """Remote branches with their git-flow kind and any naming problem."""
        return remote.branches(id)

    @tool(mcp, annotations=READ_ONLY)
    def app_tags(id: AppId) -> list[str]:
        """Tags, newest first."""
        return remote.tags(id)

    @tool(mcp, annotations=READ_ONLY)
    def app_releases(id: AppId) -> list[schemas.ReleaseRow]:
        """Releases known from tags: version, tag, sha, date, whether it is a pre-release."""
        return remote.releases(id)

    @tool(mcp, annotations=REACHES_OUT)
    def release(
        id: AppId,
        level: Annotated[
            str, Field(description="patch, minor, major or X.Y.Z")
        ] = "patch",
        dry_run: Annotated[
            bool, Field(description="true only computes the next version and changelog")
        ] = True,
        branch: Annotated[
            Optional[str],
            Field(
                description="Release from this branch instead of the current one; the clone must be clean. main/master cut a stable version, anything else an rc"
            ),
        ] = None,
    ) -> schemas.ReleasePreview:
        """Bump, changelog, tag and publish a release on the platform.

        Defaults to a dry run: show `next`, `branch` and `prerelease`, then
        call again with dry_run=false. Stable versions come only from
        main/master; any other branch produces X.Y.Z-rc.N.
        """
        return remote.release(id, level, dry_run, branch)

    @tool(mcp, annotations=REACHES_OUT)
    def start_branch(
        id: AppId,
        kind: Annotated[
            str,
            Field(
                description="feature, bugfix, hotfix, release, support, chore, docs, refactor, test, ci, perf"
            ),
        ],
        code: Annotated[str, Field(description="Issue or ticket code: 42, PROJ-123")],
        slug: Optional[str] = None,
    ) -> schemas.BranchStarted:
        """Start a git-flow branch on the app: right base, create <kind>/<code>[-slug], push it; the app is then checked out on it."""
        return remote.start_branch(id, kind, code, slug, True)

    @tool(mcp, annotations=REACHES_OUT)
    def checkout_branch(id: AppId, branch: str) -> schemas.AppEntry:
        """Check the app out on another branch of its remote. Refuses while there are uncommitted changes."""
        return remote.checkout(id, branch)

    @tool(mcp, annotations=READ_ONLY)
    def propose_pull_request(
        id: AppId, base: Optional[str] = None, title: Optional[str] = None
    ) -> schemas.PullRequestPlan:
        """Compute the pull request for the clone's current branch: target, title, body, commits. Nothing is opened."""
        return remote.propose_pr(id, base, title)

    @tool(mcp, annotations=REACHES_OUT)
    def open_pull_request(
        id: AppId,
        base: Optional[str] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        draft: bool = False,
    ) -> schemas.PullRequestOpened:
        """Open the pull request on the code host with the platform's credentials. Confirm with the user first."""
        return remote.open_pr(id, base, title, body, draft)

    @tool(mcp, annotations=READ_ONLY)
    def read_manifest(id: AppId) -> schemas.ManifestText:
        """The app's platform.toml as text."""
        return remote.manifest(id)

    @tool(mcp, annotations=REACHES_OUT)
    def write_manifest(
        id: AppId, content: Annotated[str, Field(description="Full platform.toml")]
    ) -> schemas.ConfigurationChanged:
        """Replace platform.toml in the clone. Validated as TOML; commit afterwards with commit_changes."""
        return remote.write_manifest(id, content)

    @tool(mcp, annotations=REACHES_OUT)
    def set_cloud(
        id: AppId,
        target: Annotated[str, Field(description="aws/lambda, aws/amplify, docker")],
        source: Annotated[
            Optional[str],
            Field(
                description="Name of a custom template repository from list_matrix; default official"
            ),
        ] = None,
    ) -> schemas.ConfigurationChanged:
        """Apply a deploy overlay to the clone and set [deploy] target. Commit afterwards with commit_changes."""
        return remote.set_cloud(id, target, source)

    @tool(mcp, annotations=REACHES_OUT)
    def add_service(
        id: AppId,
        name: Annotated[str, Field(description="postgres, ...")],
        provider: Optional[str] = None,
        source: Annotated[
            Optional[str],
            Field(
                description="Name of a custom template repository from list_matrix; default official"
            ),
        ] = None,
    ) -> schemas.ConfigurationChanged:
        """Add services/<name>/ to the clone. Commit afterwards with commit_changes."""
        return remote.add_service(id, name, provider, source)

    @tool(mcp, annotations=REACHES_OUT)
    def commit_changes(
        id: AppId,
        message: Annotated[str, Field(description="Conventional Commit message")],
        branch_kind: Annotated[
            Optional[str],
            Field(
                description="With branch_code: commit on a new <kind>/<code> branch first"
            ),
        ] = None,
        branch_code: Optional[str] = None,
        branch_slug: Optional[str] = None,
        pull_request: Annotated[
            bool, Field(description="Push and open a pull request for the branch")
        ] = False,
    ) -> schemas.Committed:
        """Commit what write_manifest, set_cloud or add_service changed in the clone.

        Protected branches (main, master, develop) refuse direct commits
        except chore(platform): messages — pass branch_kind and branch_code
        to move the changes onto a new branch, and pull_request=true to open
        the PR in the same call.
        """
        branch = (
            {"kind": branch_kind, "code": branch_code, "slug": branch_slug}
            if branch_kind and branch_code
            else None
        )

        return remote.commit(id, message, True, branch, pull_request)

    @tool(mcp, annotations=REACHES_OUT)
    def init_app(
        project: ProjectId,
        type: Annotated[str, Field(description="web, library, docs, plugin, empty")],
        name: Annotated[str, Field(description="Human name; the slug is derived")],
        stack: Optional[str] = None,
        template: Optional[str] = None,
        ci: Annotated[
            str, Field(description="github, gitlab, jenkins or bitbucket")
        ] = "github",
        cloud: Optional[str] = None,
        source: Annotated[
            Optional[str],
            Field(
                description="Name of a custom template repository from list_matrix; default official"
            ),
        ] = None,
        private: bool = False,
        owner: Annotated[
            Optional[str],
            Field(
                description="Account or organization on the code host that owns the new repository; default the host's default owner"
            ),
        ] = None,
    ) -> schemas.Initialized:
        """Generate a new app inside a project from a template: the repository is created on the code host attached to the organization and pushed right away — confirm with the user first."""
        row = _project_of(remote, project)

        return remote.init(
            row["id"],
            {
                "type": type,
                "stack": stack,
                "template": template,
                "name": name,
                "ci": ci,
                "cloud": cloud,
                "template_source": source,
                "github_owner": owner,
                "push": True,
                "private": private,
            },
            _org_of(row),
        )

    @tool(mcp, annotations=REACHES_OUT)
    def deploy(
        id: AppId,
        stage: Annotated[
            Optional[str], Field(description="dev or prod; default from the branch")
        ] = None,
        dry_run: Annotated[bool, Field(description="true runs preflight only")] = True,
    ) -> list[schemas.DeployResult]:
        """Ship the current version to the app's [deploy] target. Defaults to preflight; call again with dry_run=false to deploy."""
        return remote.deploy(id, stage, dry_run)

    @tool(mcp, annotations=READ_ONLY)
    def diagnose(id: AppId, stage: Optional[str] = None) -> list[schemas.Diagnosis]:
        """Health, status and URL of what is deployed."""
        return remote.diagnose(id, stage)

    @tool(mcp, annotations=READ_ONLY)
    def list_matrix() -> schemas.Matrix:
        """Project types, stacks, templates, clouds and services the platform can generate.

        Merges the official repository with every template repository the
        organization added; each entry carries its `source`, and `sources`
        lists them with their status. Pass a custom source's name to
        init_app, set_cloud and add_service.
        """
        return remote.matrix()
