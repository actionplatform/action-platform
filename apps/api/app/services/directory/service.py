"""The directory: who exists, what they own, and what they connected — organizations, projects, apps, teams, invitations, hosts, OAuth apps, template sources.

`DirectoryService` reads; `DirectoryWrites` also changes. Both are composed from one module per domain.
"""

from app.core.shared.clock import now
from app.core.shared.credentials import (
    Credentials,
    OAuthApp,
)
from app.core.shared.ids import new_id, slugify
from app.repositories.base import (
    DEFAULT_GIT_AUTHOR,
    EMAIL,
    HOST_KINDS,
    HOST_LABELS,
    INVITATION_TTL,
    PROVIDERS,
    REFRESH_MARGIN,
    DirectoryError,
)
from app.services.integrations.hosts.directory_reads import HostsReads
from app.services.integrations.hosts.directory_writes import HostsWrites
from app.repositories.organization.invitations import (
    InvitationsReads,
    InvitationsWrites,
)
from app.repositories.integrations.oauth_apps import (
    OAuthAppsReads,
    OAuthAppsWrites,
)
from app.repositories.organization.organizations import (
    OrganizationsReads,
    OrganizationsWrites,
)
from app.repositories.projects.projects import (
    ProjectsReads,
    ProjectsWrites,
)
from app.repositories.organization.teams import TeamsReads, TeamsWrites
from app.repositories.integrations.template_sources import (
    TemplateSourcesReads,
    TemplateSourcesWrites,
)


class DirectoryService(
    OrganizationsReads,
    ProjectsReads,
    TeamsReads,
    InvitationsReads,
    HostsReads,
    OAuthAppsReads,
    TemplateSourcesReads,
):
    pass


class DirectoryWrites(
    DirectoryService,
    OrganizationsWrites,
    ProjectsWrites,
    TeamsWrites,
    InvitationsWrites,
    HostsWrites,
    OAuthAppsWrites,
    TemplateSourcesWrites,
):
    pass


__all__ = [
    "DEFAULT_GIT_AUTHOR",
    "EMAIL",
    "HOST_KINDS",
    "HOST_LABELS",
    "INVITATION_TTL",
    "PROVIDERS",
    "REFRESH_MARGIN",
    "Credentials",
    "DirectoryError",
    "DirectoryService",
    "DirectoryWrites",
    "OAuthApp",
    "new_id",
    "now",
    "slugify",
]
