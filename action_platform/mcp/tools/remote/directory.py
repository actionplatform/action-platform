"""Who the token acts as, and the organization around it: organizations, projects, teams, members and invitations."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from pydantic import Field

from action_platform.mcp import schemas
from action_platform.mcp.annotations import DESTRUCTIVE, READ_ONLY, REACHES_OUT, tool
from action_platform.mcp.tools.remote.common import OrgId
from action_platform.remote.client import Remote


Role = Literal["owner", "admin", "deployer", "developer", "viewer"]
UserId = Annotated[str, Field(description="User id from list_members")]


def register(mcp: Any, remote: Remote) -> None:
    def invitation(row: schemas.InvitationRow) -> schemas.Invitation:
        return schemas.Invitation(
            **row.model_dump(), link=f"{remote.server}/invite/{row.id}"
        )

    @tool(mcp, annotations=READ_ONLY)
    def whoami() -> schemas.WhoAmI:
        """Who these tools act as and what they may do: account, organization, role, the token's scope and reach (project/app), and the permissions that result — call first when unsure whether an action is allowed."""
        who = remote.whoami()

        return {
            "server": remote.server,
            "user": who.user,
            "organization": who.organization,
            "organizations": who.organizations,
            "spans_every_organization": who.organization is None,
            "role": who.role_name,
            "scope": who.scope,
            "limited_to": {"project": who.project, "app": who.app},
            "can": dict(who.permissions),
        }

    @tool(mcp, annotations=READ_ONLY)
    def list_organizations() -> list[schemas.OrganizationRow]:
        """Every organization the account belongs to, with the role there and what a token could be granted. The current token acts on one organization only (see whoami)."""
        return remote.organizations()

    @tool(mcp, annotations=READ_ONLY)
    def list_projects(organization: OrgId = None) -> list[schemas.ProjectRow]:
        """Projects with their team and apps; limited to the token's project or app when it has one. A token that spans every organization lists them all (each with its organization) unless `organization` narrows it."""
        return remote.projects(organization=organization)

    @tool(mcp, annotations=READ_ONLY)
    def list_teams(organization: OrgId = None) -> list[schemas.TeamRow]:
        """Teams in the organization: members and the projects each team owns."""
        return remote.teams(organization=organization)

    @tool(mcp, annotations=READ_ONLY)
    def list_members(organization: OrgId = None) -> list[schemas.MemberRow]:
        """Members of the organization and their roles."""
        return remote.members(organization=organization)

    @tool(mcp, annotations=REACHES_OUT)
    def create_project(
        name: str,
        description: Annotated[str, Field(description="Optional description")] = "",
        organization: OrgId = None,
    ) -> schemas.Created:
        """Create a project in the organization (needs project.manage and an admin-scoped token)."""
        return remote.create_project(name, description, organization=organization)

    @tool(mcp, annotations=REACHES_OUT)
    def create_team(
        name: str,
        description: Annotated[str, Field(description="Optional description")] = "",
        organization: OrgId = None,
    ) -> schemas.Created:
        """Create a team in the organization (needs org.manage and an admin-scoped token)."""
        return remote.create_team(name, description, organization=organization)

    @tool(mcp, annotations=REACHES_OUT)
    def add_team_member(
        team_id: Annotated[str, Field(description="Team id from list_teams")],
        user_id: Annotated[str, Field(description="User id from list_members")],
        organization: OrgId = None,
    ) -> schemas.Ok:
        """Put an organization member on a team (needs org.manage)."""
        return remote.add_team_member(team_id, user_id, organization=organization)

    @tool(mcp, annotations=REACHES_OUT)
    def assign_project_team(
        project_id: Annotated[str, Field(description="Project id from list_projects")],
        team_id: Annotated[
            Optional[str], Field(description="Team id from list_teams; null unassigns")
        ] = None,
        organization: OrgId = None,
    ) -> schemas.Ok:
        """Give a project to a team, or take it away with team_id=null (needs project.manage)."""
        return remote.assign_project_team(
            project_id, team_id, organization=organization
        )

    @tool(mcp, annotations=REACHES_OUT)
    def set_member_role(
        user_id: Annotated[str, Field(description="User id from list_members")],
        role: Annotated[
            str, Field(description="owner, admin, deployer, developer or viewer")
        ],
        organization: OrgId = None,
    ) -> schemas.Ok:
        """Change a member's role in the organization (needs org.manage; the last owner cannot be demoted)."""
        return remote.set_member_role(user_id, role, organization=organization)

    @tool(mcp, annotations=DESTRUCTIVE)
    def remove_member(user_id: UserId, organization: OrgId = None) -> schemas.Ok:
        """Remove a person from the organization: they lose every project and team here; their account stays. Needs org.manage; only an owner removes an owner. Ask first."""
        remote.remove_member(user_id, organization=organization)

        return schemas.Ok()

    @tool(mcp, annotations=DESTRUCTIVE)
    def remove_team_member(
        team_id: Annotated[str, Field(description="Team id from list_teams")],
        user_id: UserId,
        organization: OrgId = None,
    ) -> schemas.Ok:
        """Take a member off a team; they stay in the organization (needs org.manage)."""
        remote.remove_team_member(team_id, user_id, organization=organization)

        return schemas.Ok()

    @tool(mcp, annotations=READ_ONLY)
    def list_invitations(organization: OrgId = None) -> list[schemas.Invitation]:
        """Pending invitations into the organization: email, or the code-host login for one an import made without an email, role, the teams joined on accepting, who invited, when it expires and the link that accepts it (needs org.manage)."""
        return [invitation(row) for row in remote.invitations(organization)]

    @tool(mcp, annotations=REACHES_OUT)
    def invite_member(
        email: Annotated[str, Field(description="The person's email")],
        role: Annotated[Role, Field(description="The role they get on accepting")],
        organization: OrgId = None,
    ) -> schemas.Invitation:
        """Invite a person into the organization with a role (needs org.manage). No email is sent: hand them `link`, where they sign in or sign up with that email to join. Inviting the same email again answers with the pending invitation."""
        return invitation(remote.invite(email, role, organization))

    @tool(mcp, annotations=DESTRUCTIVE)
    def cancel_invitation(
        id: Annotated[str, Field(description="Invitation id from list_invitations")],
        organization: OrgId = None,
    ) -> schemas.Ok:
        """Cancel a pending invitation; its link stops working (needs org.manage)."""
        remote.cancel_invitation(id, organization)

        return schemas.Ok()
