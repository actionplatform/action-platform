"""`ci_*` tools: read-only looks at the runs, logs and queue of a CI server a plugin brings, through the CIRunner contract."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from action_platform.mcp.annotations import READ_ONLY, tool
from action_platform.plugins import ci

Kind = Annotated[
    str,
    Field(
        description="The CI server, as its plugin registers it; empty for the only one installed"
    ),
]
Job = Annotated[
    str, Field(description="The job as the CI names it, e.g. team/app/main")
]


def register(mcp: Any) -> None:
    @tool(mcp, annotations=READ_ONLY)
    def ci_runs(
        job: Job,
        limit: Annotated[
            int, Field(description="How many, newest first", ge=1, le=100)
        ] = 20,
        kind: Kind = "",
    ) -> list[dict[str, Any]]:
        """The latest runs of a job: number, status, branch, commit, what started it, when and how long."""
        return ci.runs(ci.runner(kind), job, limit)

    @tool(mcp, annotations=READ_ONLY)
    def ci_run(
        job: Job,
        number: Annotated[int, Field(description="Run number; 0 for the latest")] = 0,
        kind: Kind = "",
    ) -> dict[str, Any]:
        """One run: status, timing, its parameters, what started it and the commits it built."""
        return ci.run(ci.runner(kind), job, number)

    @tool(mcp, annotations=READ_ONLY)
    def ci_log(
        job: Job,
        number: Annotated[int, Field(description="Run number")],
        start: Annotated[
            int,
            Field(description="Offset to read from; next_start of the last read", ge=0),
        ] = 0,
        node: Annotated[
            str,
            Field(
                description="One stage or step, by the id its stages give; empty for the whole console"
            ),
        ] = "",
        kind: Kind = "",
    ) -> dict[str, Any]:
        """A run's log from an offset: `text`, `next_start` to resume from and `more` while the run still writes."""
        return ci.log(ci.runner(kind), job, number, start, node)

    @tool(mcp, annotations=READ_ONLY)
    def ci_queue(kind: Kind = "") -> list[dict[str, Any]]:
        """What waits in the CI server's queue, since when and why."""
        return ci.queue(ci.runner(kind))
