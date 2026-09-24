"""Git-flow on an app's clone: history, branches, releases and pull requests."""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import Field

from action_platform.mcp import schemas
from action_platform.mcp.annotations import READ_ONLY, REACHES_OUT, tool
from action_platform.mcp.tools.remote.common import AppId
from action_platform.remote.client import Remote


def register(mcp: Any, remote: Remote) -> None:
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
