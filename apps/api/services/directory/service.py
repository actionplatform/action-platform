"""The directory: who exists, what they own, and what they connected — organizations, projects, apps, teams, invitations, hosts, OAuth apps, template sources.

`DirectoryService` reads; `DirectoryWrites` also changes. Both are composed from one module per domain.
"""

from action_platform_api.core.shared.clock import now
from action_platform_api.core.shared.ids import new_id, slugify
from action_platform_api.core.shared.credentials import (
    Credentials,
    OAuthApp,
)
from action_platform_api.services.directory.base import (
    DEFAULT_GIT_AUTHOR,
    EMAIL,
    HOST_KINDS,
    HOST_LABELS,
    INVITATION_TTL,
    PROVIDERS,
    REFRESH_MARGIN,
    DirectoryError,
)
from action_platform_api.services.directory.hosts import HostsReads, HostsWrites
from action_platform_api.services.directory.invitations import (
    InvitationsReads,
    InvitationsWrites,
)
from action_platform_api.services.directory.oauth_apps import (
    OAuthAppsReads,
    OAuthAppsWrites,
)
from action_platform_api.services.directory.organizations import (
    OrganizationsReads,
    OrganizationsWrites,
)
from action_platform_api.services.directory.projects import (
    ProjectsReads,
    ProjectsWrites,
)
from action_platform_api.services.directory.teams import TeamsReads, TeamsWrites
from action_platform_api.services.directory.template_sources import (
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
