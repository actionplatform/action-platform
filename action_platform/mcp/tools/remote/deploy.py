"""Scopes, readiness, deploys, diagnosis and the deployments recorded for an app."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Union

from pydantic import Field

from action_platform.core.exception import ActionPlatformError
from action_platform.mcp import schemas
from action_platform.mcp.annotations import DESTRUCTIVE, READ_ONLY, REACHES_OUT, tool
from action_platform.mcp.tools.remote.common import AppId, app_in_project, org_of
from action_platform.remote.client import Remote


Criticality = Literal["test", "low", "medium", "high", "critical"]
ScopeKind = Literal["web", "job", "worker", "static", "library"]
ScopeName = Annotated[str, Field(description="A scope name from list_scopes")]
Tag = Annotated[
    str,
    Field(
        description="The release as app_releases lists it: v1.4.0, web/v1.4.0; a bare 1.4.0 means v1.4.0"
    ),
]


def tag_of(value: str) -> str:
    value = value.strip()

    return f"v{value}" if value[:1].isdigit() else value


def register(mcp: Any, remote: Remote) -> None:
    @tool(mcp, annotations=READ_ONLY)
    def list_scopes(id: AppId) -> schemas.Scopes:
        """Where the app's releases are deployed: each scope with its kind and its criticality (test, low, medium, high, critical). Criticality decides what a scope takes: test and low take candidates, stable and hotfix releases; medium and above take stable and hotfix only. A deploy always names a scope; an app without scopes does not deploy."""
        project, app = app_in_project(remote, id)

        return remote.scopes(project.id, app.id, org_of(project))

    @tool(mcp, annotations=REACHES_OUT)
    def update_scope(
        id: AppId,
        name: ScopeName,
        criticality: Optional[Criticality] = None,
        kind: Optional[ScopeKind] = None,
    ) -> schemas.Scopes:
        """Change a scope's criticality or kind; what is not given stays. Needs app.configure. Raising the criticality narrows what the scope takes (medium and above refuse candidates). Show the change and ask first."""
        project, app = app_in_project(remote, id)
        organization = org_of(project)
        current = next(
            (
                s
                for s in remote.scopes(project.id, app.id, organization).items
                if s.name == name
            ),
            None,
        )

        if current is None:
            raise ActionPlatformError(f"no scope {name!r}: list_scopes shows them")

        return remote.update_scope(
            project.id,
            app.id,
            name,
            {
                "name": name,
                "kind": kind or current.kind,
                "criticality": criticality or current.criticality,
            },
            organization,
        )

    @tool(mcp, annotations=DESTRUCTIVE)
    def delete_scope(id: AppId, name: ScopeName) -> schemas.Scopes:
        """Delete a scope, so deploy no longer accepts it; refused while a deploy to it is running. Needs app.configure. Ask first."""
        project, app = app_in_project(remote, id)

        return remote.delete_scope(project.id, app.id, name, org_of(project))

    @tool(mcp, annotations=READ_ONLY)
    def release_readiness(
        id: AppId,
        tag: Tag,
        scope: Annotated[
            Optional[str], Field(description="Only this scope; default every scope")
        ] = None,
    ) -> list[schemas.ReadinessRow]:
        """Whether a release can reach each scope, as the release page shows it: per scope a verdict (ok, blocked, pending) and the checks with id, severity, detail and fix. A blocked verdict makes deploy refuse that scope. No row for a scope means it was never checked: recheck_readiness queues the check. Call before a deploy's dry run."""
        project, app = app_in_project(remote, id)
        rows = remote.readiness(project.id, app.id, tag_of(tag), org_of(project))

        return [row for row in rows if scope is None or row.stage == scope]

    @tool(mcp, annotations=REACHES_OUT)
    def recheck_readiness(
        id: AppId,
        tag: Tag,
        scope: Annotated[
            Optional[str], Field(description="Only this scope; default every scope")
        ] = None,
    ) -> schemas.ReadinessQueued:
        """Queue a new readiness check of a release on the worker (needs app.release): configuration, manifests, credentials, permissions and the destination's state, nothing built or changed. Answers with the job ids; follow them with job_status, then read release_readiness."""
        project, app = app_in_project(remote, id)

        return remote.check_readiness(
            project.id, app.id, tag_of(tag), scope, org_of(project)
        )

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
        background: Annotated[
            bool,
            Field(
                description="With dry_run=false: answer with the job id at once instead of following the job until it ends"
            ),
        ] = False,
    ) -> Union[list[schemas.DeployResult], schemas.JobQueued]:
        """Ship a release to one of the app's scopes. Defaults to preflight; call again with dry_run=false to deploy. Cut the release first (`release`) when none exists; the scope's criticality decides whether the release may go there, and, when `version` is given, a release whose readiness for the scope is blocked is refused (release_readiness says why). A deploy always runs as a job on the platform's worker: without background the tool follows it and answers with the results, or with the job id when it still runs after 15 minutes; with background=true it answers with the job id at once. Follow a job with job_logs and job_status."""
        if background and not dry_run:
            return remote.deploy_later(id, stage, version)

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
