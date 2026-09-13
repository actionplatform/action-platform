"""Tools that act on a hosted platform through `action-platform login`, not on the local checkout."""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import Field

from action_platform.mcp.annotations import DESTRUCTIVE, READ_ONLY, REACHES_OUT
from action_platform.remote.client import Remote

AppId = Annotated[str, Field(description="App id from list_apps")]


def register(mcp: Any, remote: Remote) -> None:
    @mcp.tool(annotations=READ_ONLY)
    def whoami() -> dict:
        """Which platform and account these tools act as."""
        who = remote.whoami().get("user", {})

        return {
            "server": remote.server,
            "email": who.get("email"),
            "name": who.get("name"),
        }

    @mcp.tool(annotations=READ_ONLY)
    def list_apps() -> list[dict]:
        """Apps the platform manages — one git repository each: id, name, url, branch, version."""
        return remote.apps()

    @mcp.tool(annotations=REACHES_OUT)
    def add_app(
        url: Annotated[str, Field(description="Git url; the platform clones it")],
        name: Optional[str] = None,
    ) -> dict:
        """Register a repository as an app on the platform. It must already contain a platform.toml."""
        return remote.add_app(url, name)

    @mcp.tool(annotations=DESTRUCTIVE)
    def remove_app(id: AppId) -> dict:
        """Unregister an app and delete the platform's clone of it. The repository itself is untouched."""
        remote.remove_app(id)

        return {"removed": id}

    @mcp.tool(annotations=REACHES_OUT)
    def sync_app(id: AppId) -> dict:
        """git fetch + fast-forward the platform's clone. Run before auditing or releasing."""
        return remote.sync_app(id)

    @mcp.tool(annotations=READ_ONLY)
    def app_info(id: AppId) -> dict:
        """platform.toml, current branch, latest tag and whether the clone is clean."""
        return remote.app(id)

    @mcp.tool(annotations=READ_ONLY)
    def gitflow_audit(id: AppId) -> dict:
        """Check the app's current branch and commits against git-flow and Conventional Commits."""
        return remote.gitflow(id)

    @mcp.tool(annotations=READ_ONLY)
    def app_commits(id: AppId, limit: int = 20) -> list[dict]:
        """Recent commits: sha, subject, author, date."""
        return remote.commits(id, limit)

    @mcp.tool(annotations=READ_ONLY)
    def app_branches(id: AppId) -> list[dict]:
        """Remote branches with their git-flow kind and any naming problem."""
        return remote.branches(id)

    @mcp.tool(annotations=READ_ONLY)
    def app_tags(id: AppId) -> list[str]:
        """Tags, newest first."""
        return remote.tags(id)

    @mcp.tool(annotations=READ_ONLY)
    def app_releases(id: AppId) -> list[dict]:
        """Releases known from tags: version, tag, sha, date, whether it is a pre-release."""
        return remote.releases(id)

    @mcp.tool(annotations=REACHES_OUT)
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
    ) -> dict:
        """Bump, changelog, tag and publish a release on the platform.

        Defaults to a dry run: show `next`, `branch` and `prerelease`, then
        call again with dry_run=false. Stable versions come only from
        main/master; any other branch produces X.Y.Z-rc.N.
        """
        return remote.release(id, level, dry_run, branch)

    @mcp.tool(annotations=REACHES_OUT)
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
        push: Annotated[bool, Field(description="Push the new branch upstream")] = True,
    ) -> dict:
        """Start a git-flow branch on the platform's clone: right base, pull, create <kind>/<code>[-slug]."""
        return remote.start_branch(id, kind, code, slug, push)

    @mcp.tool(annotations=REACHES_OUT)
    def checkout_branch(id: AppId, branch: str) -> dict:
        """Switch the platform's clone to another branch. Refuses a dirty clone."""
        return remote.checkout(id, branch)

    @mcp.tool(annotations=READ_ONLY)
    def propose_pull_request(
        id: AppId, base: Optional[str] = None, title: Optional[str] = None
    ) -> dict:
        """Compute the pull request for the clone's current branch: target, title, body, commits. Nothing is opened."""
        return remote.propose_pr(id, base, title)

    @mcp.tool(annotations=REACHES_OUT)
    def open_pull_request(
        id: AppId,
        base: Optional[str] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        draft: bool = False,
    ) -> dict:
        """Open the pull request on the code host with the platform's credentials. Confirm with the user first."""
        return remote.open_pr(id, base, title, body, draft)

    @mcp.tool(annotations=READ_ONLY)
    def read_manifest(id: AppId) -> dict:
        """The app's platform.toml as text."""
        return remote.manifest(id)

    @mcp.tool(annotations=REACHES_OUT)
    def write_manifest(
        id: AppId, content: Annotated[str, Field(description="Full platform.toml")]
    ) -> dict:
        """Replace platform.toml in the clone. Validated as TOML; commit afterwards with commit_changes."""
        return remote.write_manifest(id, content)

    @mcp.tool(annotations=REACHES_OUT)
    def set_cloud(
        id: AppId,
        target: Annotated[str, Field(description="aws/lambda, aws/amplify, docker")],
        source: Annotated[
            Optional[str],
            Field(
                description="Name of a custom template repository from list_matrix; default official"
            ),
        ] = None,
    ) -> dict:
        """Apply a deploy overlay to the clone and set [deploy] target. Commit afterwards with commit_changes."""
        return remote.set_cloud(id, target, source)

    @mcp.tool(annotations=REACHES_OUT)
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
    ) -> dict:
        """Add services/<name>/ to the clone. Commit afterwards with commit_changes."""
        return remote.add_service(id, name, provider, source)

    @mcp.tool(annotations=REACHES_OUT)
    def commit_changes(
        id: AppId,
        message: Annotated[str, Field(description="Conventional Commit message")],
        push: bool = False,
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
    ) -> dict:
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

        return remote.commit(id, message, push, branch, pull_request)

    @mcp.tool(annotations=REACHES_OUT)
    def init_app(
        type: Annotated[str, Field(description="web, library, docs, plugin, empty")],
        name: Annotated[str, Field(description="Human name; the slug is derived")],
        stack: Optional[str] = None,
        template: Optional[str] = None,
        ci: Annotated[str, Field(description="github, gitlab or jenkins")] = "github",
        cloud: Optional[str] = None,
        source: Annotated[
            Optional[str],
            Field(
                description="Name of a custom template repository from list_matrix; default official"
            ),
        ] = None,
        push: Annotated[
            bool, Field(description="Create the repository on the code host and push")
        ] = False,
        private: bool = False,
    ) -> dict:
        """Generate a new app on the platform from a template and register it. With push=true the repository is created on the code host — confirm with the user first."""
        return remote.init(
            {
                "type": type,
                "stack": stack,
                "template": template,
                "name": name,
                "ci": ci,
                "cloud": cloud,
                "source": source,
                "push": push,
                "private": private,
            }
        )

    @mcp.tool(annotations=REACHES_OUT)
    def deploy(
        id: AppId,
        stage: Annotated[
            Optional[str], Field(description="dev or prod; default from the branch")
        ] = None,
        dry_run: Annotated[bool, Field(description="true runs preflight only")] = True,
    ) -> list[dict]:
        """Ship the current version to the app's [deploy] target. Defaults to preflight; call again with dry_run=false to deploy."""
        return remote.deploy(id, stage, dry_run)

    @mcp.tool(annotations=READ_ONLY)
    def diagnose(id: AppId, stage: Optional[str] = None) -> list[dict]:
        """Health, status and URL of what is deployed."""
        return remote.diagnose(id, stage)

    @mcp.tool(annotations=READ_ONLY)
    def list_matrix() -> dict:
        """Project types, stacks, templates, clouds and services the platform can generate.

        Merges the official repository with every template repository the
        organization added; each entry carries its `source`, and `sources`
        lists them with their status. Pass a custom source's name to
        init_app, set_cloud and add_service.
        """
        return remote.matrix()
