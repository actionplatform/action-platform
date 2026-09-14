"""The directory: who exists, what they own, and what they connected — organizations, projects, apps, teams, invitations, hosts, OAuth apps, template sources.

`DirectoryService` reads; `DirectoryWrites` also changes. Both are composed from one module per domain.
"""

from action_platform.api.services.shared.common import (
    kind_of_url,
    new_id,
    now,
    repo_from_url,
    slugify,
)
from action_platform.api.services.shared.credentials import (
    Credentials,
    OAuthApp,
    oauth_app_for,
    refresh_oauth,
)
from action_platform.api.services.directory.base import (
    DEFAULT_GIT_AUTHOR,
    EMAIL,
    HOST_KINDS,
    HOST_LABELS,
    INVITATION_TTL,
    PROVIDERS,
    REFRESH_MARGIN,
    DirectoryError,
)
from action_platform.api.services.directory.hosts import HostsReads, HostsWrites
from action_platform.api.services.directory.invitations import (
    InvitationsReads,
    InvitationsWrites,
)
from action_platform.api.services.directory.oauth_apps import (
    OauthAppsReads,
    OauthAppsWrites,
)
from action_platform.api.services.directory.organizations import (
    OrganizationsReads,
    OrganizationsWrites,
)
from action_platform.api.services.directory.projects import (
    ProjectsReads,
    ProjectsWrites,
)
from action_platform.api.services.directory.teams import TeamsReads, TeamsWrites
from action_platform.api.services.directory.template_sources import (
    TemplateSourcesReads,
    TemplateSourcesWrites,
)


class DirectoryService(
    OrganizationsReads,
    ProjectsReads,
    TeamsReads,
    InvitationsReads,
    HostsReads,
    OauthAppsReads,
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
    OauthAppsWrites,
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
    "kind_of_url",
    "new_id",
    "now",
    "oauth_app_for",
    "refresh_oauth",
    "repo_from_url",
    "slugify",
]
