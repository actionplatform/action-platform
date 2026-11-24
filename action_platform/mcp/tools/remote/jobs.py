"""Jobs the platform's worker runs: an import, a readiness check, a deploy started in the background."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from action_platform.mcp import schemas
from action_platform.mcp.annotations import READ_ONLY, tool
from action_platform.remote.client import Remote

JobId = Annotated[
    str,
    Field(
        description="The job id a tool answered with (import_organization, recheck_readiness, deploy with background=true)"
    ),
]


def register(mcp: Any, remote: Remote) -> None:
    @tool(mcp, annotations=READ_ONLY)
    def job_status(job_id: JobId) -> schemas.Job:
        """Where a job stands: queued, running, done or failed, with its result or error once it finished."""
        return remote.job(job_id)

    @tool(mcp, annotations=READ_ONLY)
    def job_logs(
        job_id: JobId,
        after: Annotated[
            int,
            Field(
                ge=0,
                description="Lines already read: pass the `next` of the previous answer to get only new ones",
            ),
        ] = 0,
    ) -> schemas.JobLogs:
        """What the worker wrote while running a job, from line `after` on. `finished` false means more may come: call again with after=next until it is true."""
        return remote.job_logs(job_id, after=after)
