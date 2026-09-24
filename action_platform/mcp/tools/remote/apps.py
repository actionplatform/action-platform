"""Apps inside projects: list, register, generate, remove, sync and inspect the platform's clone."""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import Field

from action_platform.mcp import schemas
from action_platform.mcp.annotations import DESTRUCTIVE, READ_ONLY, REACHES_OUT, tool
from action_platform.mcp.tools.remote.common import (
    AppId,
    ProjectId,
    OrgId,
    org_of,
    project_of,
    app_in_project,
)
from action_platform.remote.client import Remote


def register(mcp: Any, remote: Remote) -> None:
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
        row = project_of(remote, project)

        return remote.add_app(row.id, url, install, org_of(row))

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
        project, app = app_in_project(remote, id)

        return remote.remove_app(project.id, app.id, repository, org_of(project))

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
        row = project_of(remote, project)

        return remote.delete_project(row.id, repositories, org_of(row))

    @tool(mcp, annotations=REACHES_OUT)
    def sync_app(id: AppId) -> schemas.AppEntry:
        """git fetch + fast-forward the platform's clone. Run before auditing or releasing."""
        return remote.sync_app(id)

    @tool(mcp, annotations=READ_ONLY)
    def app_info(id: AppId) -> schemas.AppDetail:
        """platform.toml, current branch, latest tag and whether the clone is clean."""
        return remote.app(id)

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
        row = project_of(remote, project)

        return remote.init(
            row.id,
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
            org_of(row),
        )
