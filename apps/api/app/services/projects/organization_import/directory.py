"""The one place that legitimately spans organization, projects and integrations on a single session: importing a code-host organization creates all three."""

from app.repositories.organization import OrganizationRepository
from app.repositories.projects import ProjectsRepository
from app.services.integrations.hosts.directory import IntegrationsDirectory


class ImportDirectory(
    OrganizationRepository, ProjectsRepository, IntegrationsDirectory
):
    pass


__all__ = ["ImportDirectory"]
