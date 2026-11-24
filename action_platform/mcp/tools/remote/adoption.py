"""Bring what already exists onto the platform: a GitHub organization's repositories, teams and people, and the code host each app reads from."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from pydantic import Field

from action_platform.mcp import schemas
from action_platform.mcp.annotations import READ_ONLY, REACHES_OUT, tool
from action_platform.mcp.tools.remote.common import AppId, OrgId, app_in_project, org_of
from action_platform.remote.client import Remote

HostId = Annotated[str, Field(description="A GitHub code host id from list_hosts")]
Login = Annotated[
    str,
    Field(
        description="The GitHub organization (or account) login, from list_import_organizations"
    ),
]


def register(mcp: Any, remote: Remote) -> None:
    @tool(mcp, annotations=READ_ONLY)
    def list_hosts(organization: OrgId = None) -> list[schemas.HostRow]:
        """Code hosts connected to the organization (GitHub, GitLab, Bitbucket): id, kind, account and how it is authorised — never the token."""
        return remote.hosts(organization)

    @tool(mcp, annotations=REACHES_OUT)
    def set_app_host(
        id: AppId,
        host: Annotated[
            Optional[str],
            Field(
                description="Code host id from list_hosts; null clears it, and the clone goes without credentials (public repositories only)"
            ),
        ] = None,
    ) -> schemas.AppHost:
        """Choose which connected code host, and so which token, the app's clone, pushes and pull requests use (needs app.flow) — the fix when a private repository answers 401."""
        project, app = app_in_project(remote, id)

        return remote.set_app_host(project.id, app.id, host, org_of(project))

    @tool(mcp, annotations=READ_ONLY)
    def list_import_organizations(
        host: HostId, organization: OrgId = None
    ) -> schemas.ImportOrganizations:
        """The GitHub organizations and the account the code host can read (needs org.manage). `install_url` installs the GitHub App on another organization when one is missing."""
        return remote.import_organizations(host, organization)

    @tool(mcp, annotations=READ_ONLY)
    def preview_organization_import(
        host: HostId, login: Login, organization: OrgId = None
    ) -> schemas.ImportPreview:
        """What importing a GitHub organization would bring (needs org.manage): its repositories (imported_as when already an app), projects, teams (exists when already a team) and people with their GitHub role (org_admin, team_maintainer, member) and a status — member, user (has an account), invited, invitable (by email), invitable_login (invited by GitHub login, verified when they accept), or no_email (no email and no GitHub OAuth app to verify a login). Show it and let the user pick before import_organization."""
        return remote.import_preview(host, login, organization)

    @tool(mcp, annotations=REACHES_OUT)
    def import_organization(
        host: HostId,
        login: Login,
        repositories: Annotated[
            list[str],
            Field(description="full_name of each repository to bring in as an app"),
        ],
        teams: Annotated[
            Optional[list[str]], Field(description="Team slugs to recreate")
        ] = None,
        people: Annotated[
            Optional[list[str]],
            Field(
                description="Logins to invite; no email is sent, list_invitations has the links"
            ),
        ] = None,
        role: Literal["admin", "deployer", "developer", "viewer"] = "developer",
        roles: Annotated[
            Optional[dict[str, Literal["admin", "deployer", "developer", "viewer"]]],
            Field(
                description="Platform role per GitHub role (org_admin, team_maintainer, member); a GitHub role left out gets `role`"
            ),
        ] = None,
        people_roles: Annotated[
            Optional[dict[str, Literal["admin", "deployer", "developer", "viewer"]]],
            Field(description="Platform role per login, over `roles`"),
        ] = None,
        project: Annotated[
            Optional[str],
            Field(
                description="Project id from list_projects for the repositories no GitHub project places; default a project of their own each"
            ),
        ] = None,
        organization: OrgId = None,
    ) -> schemas.JobQueued:
        """Import the picked repositories, teams and people of a GitHub organization (needs org.manage and an admin-scoped token). Runs as a job: the answer is its id — follow it with job_status, whose result lists the projects, apps, teams, members, invitations by email and by login, the teams waiting for each invitee, and what was skipped. Show the preview and ask first."""
        return remote.import_organization(
            {
                "host_id": host,
                "organization": login,
                "repositories": repositories,
                "teams": teams or [],
                "people": people or [],
                "role": role,
                "roles": roles or {},
                "people_roles": people_roles or {},
                "project_id": project,
            },
            organization,
        )
