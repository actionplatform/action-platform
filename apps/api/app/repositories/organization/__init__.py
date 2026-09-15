"""Organization: organizations and their members, teams, invitations — reads and writes on one session."""

from app.repositories.organization.invitations import (
    InvitationsReads,
    InvitationsWrites,
)
from app.repositories.organization.organizations import (
    OrganizationsReads,
    OrganizationsWrites,
)
from app.repositories.organization.teams import TeamsReads, TeamsWrites


class OrganizationRepository(
    OrganizationsWrites,
    TeamsWrites,
    InvitationsWrites,
    OrganizationsReads,
    TeamsReads,
    InvitationsReads,
):
    pass


__all__ = ["OrganizationRepository"]
