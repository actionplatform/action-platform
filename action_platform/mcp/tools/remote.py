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

    @mcp.tool(annotations=REACHES_OUT)
    def release(
        id: AppId,
        level: Annotated[
            str, Field(description="patch, minor, major or X.Y.Z")
        ] = "patch",
        dry_run: Annotated[
            bool, Field(description="true only computes the next version and changelog")
        ] = True,
    ) -> dict:
        """Bump, changelog, tag and publish a release on the platform. Defaults to a dry run: show it, then call again with dry_run=false."""
        return remote.release(id, level, dry_run)

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
        """Project types, stacks, templates, clouds and services the platform can generate."""
        return remote.matrix()
