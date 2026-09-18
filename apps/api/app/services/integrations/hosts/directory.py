"""The integrations an organization connected, on one session: code hosts (credentials refreshed through their providers), CI servers, OAuth apps, template sources."""

from app.repositories.integrations import (
    CiHostsReads,
    CiHostsWrites,
    OAuthAppsReads,
    OAuthAppsWrites,
    TemplateSourcesReads,
    TemplateSourcesWrites,
)
from app.services.integrations.hosts.directory_reads import HostsReads
from app.services.integrations.hosts.directory_writes import HostsWrites


class IntegrationsDirectory(
    HostsWrites,
    CiHostsWrites,
    OAuthAppsWrites,
    TemplateSourcesWrites,
    HostsReads,
    CiHostsReads,
    OAuthAppsReads,
    TemplateSourcesReads,
):
    pass


__all__ = ["IntegrationsDirectory"]
