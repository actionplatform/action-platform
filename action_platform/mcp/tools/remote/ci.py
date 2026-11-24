"""The CI an app's pipeline runs on: the organization's CI servers, the app's link to a job, its runs and starting one."""

from __future__ import annotations

import os
import re
from typing import Annotated, Any, Literal, Optional

from pydantic import Field

from action_platform.core.exception import ActionPlatformError
from action_platform.mcp import schemas
from action_platform.mcp.annotations import READ_ONLY, REACHES_OUT, tool
from action_platform.mcp.tools.remote.common import AppId, OrgId, app_in_project, org_of
from action_platform.remote.client import Remote

ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
CiHostId = Annotated[str, Field(description="CI server id from list_ci_hosts")]


def token_from(variable: str) -> str:
    if not ENV_NAME.match(variable):
        raise ActionPlatformError(f"{variable!r} is not an environment variable name")

    token = os.environ.get(variable, "").strip()

    if not token:
        raise ActionPlatformError(
            f"{variable} is not set where this MCP server runs: export it and restart the server"
        )

    return token


def register(mcp: Any, remote: Remote) -> None:
    @tool(mcp, annotations=READ_ONLY)
    def get_app_ci(
        id: AppId,
        sync: Annotated[
            bool,
            Field(description="true asks the CI for new runs first (needs app.sync)"),
        ] = False,
    ) -> schemas.CiRuns:
        """The app's CI: `link` says which runner it reads (jenkins with ci_host_id and job, github_actions or gitlab_ci from the code host, none) and `runs` the latest runs imported from it; `error` is what the CI answered when a sync failed."""
        project, app = app_in_project(remote, id)
        organization = org_of(project)

        if sync:
            return remote.sync_app_ci(project.id, app.id, organization)

        return remote.app_ci(project.id, app.id, organization)

    @tool(mcp, annotations=REACHES_OUT)
    def set_app_ci(
        id: AppId,
        job: Annotated[
            str,
            Field(
                description="The job's path on the CI server: folder/name, or folder/name/branch for a multibranch job"
            ),
        ] = "",
        ci_host: Annotated[
            Optional[str],
            Field(
                description="CI server id from list_ci_hosts; null reads the code host's own CI (GitHub Actions, GitLab CI)"
            ),
        ] = None,
    ) -> schemas.CiLink:
        """Point the app at the pipeline that already builds it, so get_app_ci and run_ci read and start it (needs app.configure)."""
        project, app = app_in_project(remote, id)

        return remote.link_app_ci(project.id, app.id, ci_host, job, org_of(project))

    @tool(mcp, annotations=REACHES_OUT)
    def run_ci(
        id: AppId,
        ref: Annotated[str, Field(min_length=1, description="Branch or tag to build")],
    ) -> schemas.CiStarted:
        """Start the app's linked pipeline on a branch or tag (needs app.flow). Whatever the pipeline does — tests, a deploy — runs; ask first. Follow it with get_app_ci(sync=true)."""
        project, app = app_in_project(remote, id)

        return remote.run_ci(project.id, app.id, ref, org_of(project))

    @tool(mcp, annotations=READ_ONLY)
    def list_ci_hosts(organization: OrgId = None) -> list[schemas.CiHostRow]:
        """CI servers connected to the organization (never their tokens)."""
        return remote.ci_hosts(organization)

    @tool(mcp, annotations=REACHES_OUT)
    def add_ci_host(
        base_url: Annotated[
            str, Field(description="The server's URL: https://ci.example.com")
        ],
        token_env: Annotated[
            str,
            Field(
                description="Name of the environment variable, where this MCP server runs, that holds the API token; never the token itself"
            ),
        ],
        username: Annotated[
            str, Field(description="The account the token belongs to")
        ] = "",
        name: Annotated[str, Field(description="A label; default Jenkins")] = "",
        kind: Literal["jenkins"] = "jenkins",
        organization: OrgId = None,
    ) -> schemas.CiHostRow:
        """Connect a CI server to the organization (needs org.manage and an admin-scoped token). The token is read from `token_env` on this machine and sealed on the platform; ask the user to export it rather than typing it into the chat. test_ci_host checks it afterwards."""
        return remote.add_ci_host(
            kind, base_url, token_from(token_env), username, name, organization
        )

    @tool(mcp, annotations=READ_ONLY)
    def test_ci_host(id: CiHostId, organization: OrgId = None) -> schemas.CiHostTest:
        """Reach a connected CI server with its stored token: ok, or the error it answered."""
        return remote.test_ci_host(id, organization)
