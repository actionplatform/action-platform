"""platform.toml, deploy overlays and services in an app's clone, and the commit that keeps them."""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import Field

from action_platform.mcp import schemas
from action_platform.mcp.annotations import READ_ONLY, REACHES_OUT, tool
from action_platform.mcp.tools.remote.common import AppId
from action_platform.remote.client import Remote


def register(mcp: Any, remote: Remote) -> None:
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
