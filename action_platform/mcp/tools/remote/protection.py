"""Git-flow enforced on the code host: what an app's host enforces, rule by rule, and applying the platform's rules."""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import Field

from action_platform.mcp import schemas
from action_platform.mcp.annotations import READ_ONLY, REACHES_OUT, tool
from action_platform.mcp.tools.remote.common import AppId, app_in_project, org_of
from action_platform.remote.client import Remote


def register(mcp: Any, remote: Remote) -> None:
    @tool(mcp, annotations=READ_ONLY)
    def protection_status(
        id: AppId,
        refresh: Annotated[
            bool,
            Field(description="true reads the code host now instead of the last check"),
        ] = False,
    ) -> schemas.Protection:
        """Whether the app's code host enforces git-flow: `enforce` (and whether the app or the organization default decides), and per rule — direct push, force push, deletion, pull request, required checks, branch names, Conventional Commits — `native` (the host refuses it), `check` (a required CI check refuses it) or `inactive` with the reason; `drift` lists what differs from the policy."""
        project, app = app_in_project(remote, id)

        return remote.protection(project.id, app.id, refresh, org_of(project))

    @tool(mcp, annotations=REACHES_OUT)
    def apply_protection(
        id: AppId,
        enforce: Annotated[
            Optional[bool],
            Field(
                description="true turns enforcement on for this app and queues a job that applies the rules (job_id; kept and reapplied when the host drifts), false off; null leaves the setting and applies once, now"
            ),
        ] = None,
    ) -> schemas.Protection:
        """Apply the git-flow rules to the app's protected branches on the code host (needs app.configure): no direct push, force push or deletion, merges only through a pull request whose checks pass; only the platform's own account may push release commits. Changes who can push to the repository — ask first."""
        project, app = app_in_project(remote, id)
        organization = org_of(project)

        if enforce is not None:
            return remote.set_protection(project.id, app.id, enforce, organization)

        return remote.apply_protection(project.id, app.id, organization)
