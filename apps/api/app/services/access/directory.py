"""What the gate reads to decide a call, on one session: the app behind a registry id and its reach (projects), the caller's organizations (organization), template sources and host credentials for enrichment (integrations)."""

from app.repositories.organization import OrganizationRepository
from app.repositories.projects import ProjectsRepository
from app.services.integrations.hosts.directory import IntegrationsDirectory


class AccessDirectory(
    ProjectsRepository, OrganizationRepository, IntegrationsDirectory
):
    pass


__all__ = ["AccessDirectory"]
