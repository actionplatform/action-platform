"""Scopes, deploys, diagnosis and the deployments recorded for an app."""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import Field

from action_platform.mcp import schemas
from action_platform.mcp.annotations import READ_ONLY, REACHES_OUT, tool
from action_platform.mcp.tools.remote.common import AppId, app_in_project
from action_platform.remote.client import Remote


def register(mcp: Any, remote: Remote) -> None:
    @tool(mcp, annotations=READ_ONLY)
    def list_scopes(id: AppId) -> schemas.Scopes:
        """Where the app's releases are deployed: each scope with its kind and its criticality (test, low, medium, high, critical). Criticality decides what a scope takes: test and low take candidates, stable and hotfix releases; medium and above take stable and hotfix only. A deploy always names a scope; an app without scopes does not deploy."""
        project, app = app_in_project(remote, id)

        return remote.scopes(project.id, app.id)

    @tool(mcp, annotations=REACHES_OUT)
    def create_scope(
        id: AppId,
        name: Annotated[
            str,
            Field(description="Unique within the app: staging, prod-eu, nightly-jobs"),
        ],
        criticality: Annotated[
            str, Field(description="test | low | medium | high | critical")
        ] = "low",
        kind: Annotated[
            str, Field(description="web | job | worker | static | library")
        ] = "web",
    ) -> schemas.Scopes:
        """Create a scope for the app. Show the user what will exist before calling."""
        project, app = app_in_project(remote, id)

        return remote.create_scope(
            project.id,
            app.id,
            {"name": name, "kind": kind, "criticality": criticality},
        )

    @tool(mcp, annotations=REACHES_OUT)
    def deploy(
        id: AppId,
        stage: Annotated[
            Optional[str],
            Field(
                description="The scope to deploy to (list_scopes); default from the branch: prod on main, dev elsewhere"
            ),
        ] = None,
        dry_run: Annotated[bool, Field(description="true runs preflight only")] = True,
        version: Annotated[
            Optional[str],
            Field(
                description="Release to ship (tag v<version>); default: the tag the app's checkout sits on. A deploy never ships an untagged tree"
            ),
        ] = None,
    ) -> list[schemas.DeployResult]:
        """Ship a release to one of the app's scopes. Defaults to preflight; call again with dry_run=false to deploy. Cut the release first (`release`) when none exists; the scope's criticality decides whether the release may go there."""
        return remote.deploy(id, stage, dry_run, version)

    @tool(mcp, annotations=READ_ONLY)
    def diagnose(id: AppId, stage: Optional[str] = None) -> list[schemas.Diagnosis]:
        """Health, status and URL of what is deployed."""
        return remote.diagnose(id, stage)

    @tool(mcp, annotations=READ_ONLY)
    def list_deployments(
        id: AppId,
        sync: Annotated[
            bool,
            Field(
                description="true asks the observed pipelines (GitHub Actions, Jenkins) for new runs and verifies versions at their destinations first"
            ),
        ] = False,
    ) -> schemas.Deployments:
        """The app's deploy targets — where releases go and who ships them — and what arrived at each, whoever executed it: the platform's worker, a workflow, a Jenkins job or a person. `verified` means the version was found at the destination."""
        project, app = app_in_project(remote, id)

        if sync:
            return remote.sync_deployments(project.id, app.id)

        return remote.deployments(project.id, app.id)

    @tool(mcp, annotations=REACHES_OUT)
    def record_deployment(
        id: AppId,
        target: Annotated[
            str, Field(description="A target name from list_deployments")
        ],
        version: Annotated[
            str, Field(description="The release that was shipped: 1.4.0 or v1.4.0")
        ],
        stage: Optional[str] = None,
        url: Annotated[
            Optional[str], Field(description="Where it can be seen, if anywhere")
        ] = None,
        ok: Annotated[
            bool, Field(description="false records a failed delivery")
        ] = True,
    ) -> schemas.DeploymentRow:
        """Record a deployment someone made outside the platform — a release that reached a target by hand or by a pipeline the platform does not observe. A deployment always references a release: `version` must be a tag."""
        project, app = app_in_project(remote, id)

        return remote.record_deployment(
            project.id, app.id, target, version, stage, url, None, ok
        )
