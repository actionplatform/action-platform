"""Release and operate: release, deploy, rollback, diagnose."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Optional

from pydantic import Field

from action_platform.core.action_platform import ActionPlatform
from action_platform.core.config import Config
from action_platform.mcp.annotations import DESTRUCTIVE, READ_ONLY, REACHES_OUT
from action_platform.settings import settings

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
    root = Path(project).resolve() if project else Path.cwd()

    return ActionPlatform(
        config=Config.from_toml(root / settings.CONFIG_FILE), repo_root=root
    )


def register(mcp: Any) -> None:
    @mcp.tool(annotations=REACHES_OUT)
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
    ) -> dict:
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

    @mcp.tool(annotations=REACHES_OUT)
    def deploy(
        project: ProjectDir = None,
        stage: Stage = None,
        dry_run: Annotated[bool, Field(description="true runs preflight only")] = True,
    ) -> list[dict]:
        """Ship the current version to the [deploy] target of platform.toml.

        Defaults to a dry run (preflight). Needs a deploy provider installed
        for the target; the error says which one is missing.
        """
        results = _tool(project).deploy(stage=stage, dry_run=dry_run)

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

    @mcp.tool(annotations=DESTRUCTIVE)
    def rollback(
        to_version: Annotated[
            Optional[str],
            Field(description="Version to return to; default is the previous one"),
        ] = None,
        project: ProjectDir = None,
        stage: Stage = None,
    ) -> dict:
        """Return the deployed target to a previous version. Confirm with the user first."""
        _tool(project).rollback(to_version=to_version, stage=stage)

        return {"rolled_back_to": to_version or "previous"}

    @mcp.tool(annotations=READ_ONLY)
    def diagnose(project: ProjectDir = None, stage: Stage = None) -> list[dict]:
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
