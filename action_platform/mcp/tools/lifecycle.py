"""Release and operate: release, scopes, readiness, deploy, rollback, diagnose, and what the hosted platform knows of a deploy."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Optional

from pydantic import Field

from action_platform.bootstrap import project as bootstrap_project
from action_platform.core.config import Config
from action_platform.core.exception import ActionPlatformError
from action_platform.core.facade import ActionPlatform
from action_platform.core.files import CONFIG_FILE
from action_platform.core.scopes import CRITICALITIES, KINDS
from action_platform.mcp import schemas
from action_platform.mcp.annotations import DESTRUCTIVE, READ_ONLY, REACHES_OUT, tool
from action_platform.remote.client import Remote

ProjectDir = Annotated[
    Optional[str], Field(description="Project directory; default is the cwd.")
]
Stage = Annotated[
    Optional[str],
    Field(
        description="dev or prod; default comes from the branch (main/master → prod)."
    ),
]


def _tool(project: Optional[str]) -> ActionPlatform:
    return bootstrap_project(Path(project).resolve() if project else None)


def _root(project: Optional[str]) -> Path:
    return Path(project).resolve() if project else Path.cwd()


def _hosted_app(
    remote: Remote, app: Optional[str], project: Optional[str]
) -> tuple[str, str]:
    """(project id, app id) on the platform for an app id or name, by default the checkout's project name."""
    wanted = app or Config.from_toml(_root(project) / CONFIG_FILE).project_name

    for row in remote.projects():
        for entry in row.apps:
            if wanted in (entry.registry_id, entry.id, entry.name):
                return row.id, entry.id

    raise ActionPlatformError(
        f"no app {wanted!r} on the platform you are logged in to: pass `app` with its id or name"
    )


def register(mcp: Any) -> None:
    @tool(mcp, annotations=REACHES_OUT)
    def release(
        level: Annotated[
            str, Field(description="patch, minor, major or X.Y.Z")
        ] = "patch",
        project: ProjectDir = None,
        dry_run: Annotated[
            bool, Field(description="true only computes the next version and changelog")
        ] = True,
        component: Annotated[
            Optional[str],
            Field(
                description="A [components.<name>] of platform.toml, e.g. web; default the repository"
            ),
        ] = None,
    ) -> schemas.ReleasePlan:
        """Bump version, write CHANGELOG, tag, push and publish a release.

        Defaults to a dry run. Show the user the next version and changelog,
        then call again with dry_run=false to publish. Off main/master the
        version becomes X.Y.Z-rc.N and the release is marked pre-release.
        """
        ctx = _tool(project).release(level=level, dry_run=dry_run, component=component)

        return {
            "current": ctx.current_version,
            "next": ctx.next_version,
            "changelog": ctx.changelog,
            "dry_run": dry_run,
        }

    @tool(mcp, annotations=READ_ONLY)
    def list_scopes(project: ProjectDir = None) -> schemas.ScopeSpecs:
        """Where this repository's releases are deployed: `[[scopes]]` of platform.toml, each with its kind and criticality (test, low, medium, high, critical). Criticality decides what a scope takes: test and low take candidates, stable and hotfix releases; medium and above take stable and hotfix only. No scopes, no deploy."""
        config = Config.from_toml(_root(project) / CONFIG_FILE)

        return {
            "items": [
                {"name": s.name, "kind": s.kind, "criticality": s.criticality}
                for s in config.scopes
            ],
            "kinds": list(KINDS),
            "criticalities": list(CRITICALITIES),
        }

    @tool(mcp, annotations=READ_ONLY)
    def readiness(
        scope: Annotated[
            Optional[str],
            Field(
                description="A scope from list_scopes; default comes from the branch (main/master → prod)"
            ),
        ] = None,
        version: Annotated[
            Optional[str],
            Field(
                description="Release to check (tag v<version>); default: the tag HEAD sits on"
            ),
        ] = None,
        target: Annotated[
            Optional[str],
            Field(description="Only this [deploy] target; default every one"),
        ] = None,
        project: ProjectDir = None,
    ) -> schemas.ReadinessRow:
        """Whether a release can reach a scope: configuration, manifests, credentials, permissions and the destination's state, each check with id, severity, detail and fix. Nothing is built or changed. verdict `blocked` means deploy will fail there: show the failing checks and their fixes instead of deploying. Call before deploy's dry run."""
        tool_ = _tool(project)
        stage = scope or tool_.releaser.context().stage
        checks = tool_.check_readiness(stage, version=version, target=target)
        blocked = any(c.blocking for c in checks)

        return {
            "stage": stage,
            "status": "done",
            "verdict": "blocked" if blocked else "ok",
            "ok": not blocked,
            "checks": [
                {
                    "id": c.id,
                    "ok": c.ok,
                    "detail": c.detail,
                    "level": c.level,
                    "severity": c.severity,
                    "fix": c.fix,
                    "target": c.target,
                }
                for c in checks
            ],
        }

    @tool(mcp, annotations=READ_ONLY)
    def job_logs(
        job_id: Annotated[
            str,
            Field(description="A job id the hosted platform answered with"),
        ],
        after: Annotated[
            int,
            Field(
                ge=0,
                description="Lines already read: pass the `next` of the previous answer to get only new ones",
            ),
        ] = 0,
    ) -> schemas.JobLogs:
        """What the hosted platform's worker wrote while running a job — a deploy, a release, a readiness check — from line `after` on. Needs `action-platform login`. `finished` false means more may come: call again with after=next."""
        return Remote.from_credentials().job_logs(job_id, after=after)

    @tool(mcp, annotations=REACHES_OUT)
    def record_deployment(
        target: Annotated[
            str, Field(description="A target name of [deploy] in platform.toml")
        ],
        version: Annotated[
            str, Field(description="The release that was shipped: 1.4.0 or v1.4.0")
        ],
        stage: Annotated[
            Optional[str], Field(description="The scope it reached")
        ] = None,
        url: Annotated[
            Optional[str], Field(description="Where it can be seen, if anywhere")
        ] = None,
        failed: Annotated[
            bool, Field(description="true records a failed delivery")
        ] = False,
        app: Annotated[
            Optional[str],
            Field(
                description="App id or name on the platform; default this repository's project name"
            ),
        ] = None,
        project: ProjectDir = None,
    ) -> schemas.DeploymentRow:
        """Record on the hosted platform a deployment made outside it — by hand, or by a pipeline the platform does not observe. Needs `action-platform login`. A deployment always references a release: `version` must be a tag."""
        remote = Remote.from_credentials()
        project_id, app_id = _hosted_app(remote, app, project)

        return remote.record_deployment(
            project_id, app_id, target, version, stage, url, None, not failed
        )

    @tool(mcp, annotations=REACHES_OUT)
    def deploy(
        project: ProjectDir = None,
        stage: Stage = None,
        dry_run: Annotated[bool, Field(description="true runs preflight only")] = True,
        version: Annotated[
            Optional[str],
            Field(
                description="Release to ship (its tag v<version>); default: the tag HEAD sits on. A deploy never ships an untagged tree"
            ),
        ] = None,
    ) -> list[schemas.DeployResult]:
        """Ship a release to the [deploy] target of platform.toml.

        Defaults to a dry run (preflight). The release must exist — cut it
        with `release` first. Needs a deploy provider installed for the
        target; the error says which one is missing.
        """
        results = _tool(project).deploy(stage=stage, dry_run=dry_run, version=version)

        return [
            {
                "target": r.target,
                "ok": r.ok,
                "version": r.version,
                "url": r.url,
                "error": r.error,
            }
            for r in results
        ]

    @tool(mcp, annotations=DESTRUCTIVE)
    def rollback(
        to_version: Annotated[
            Optional[str],
            Field(description="Version to return to; default is the previous one"),
        ] = None,
        project: ProjectDir = None,
        stage: Stage = None,
    ) -> schemas.RolledBack:
        """Return the deployed target to a previous version. Confirm with the user first."""
        _tool(project).rollback(to_version=to_version, stage=stage)

        return {"rolled_back_to": to_version or "previous"}

    @tool(mcp, annotations=READ_ONLY)
    def diagnose(
        project: ProjectDir = None, stage: Stage = None
    ) -> list[schemas.Diagnosis]:
        """Health, status and URL of the deployed target."""
        results = _tool(project).diagnose(stage=stage)

        return [
            {
                "target": d.target,
                "ok": d.ok,
                "status": d.status,
                "url": d.url,
                "details": d.details,
            }
            for d in results
        ]
