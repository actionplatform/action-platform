"""The integrations an organization connected, on one session: code hosts (credentials refreshed through their providers), OAuth apps, template sources."""

from app.repositories.integrations import (
    OAuthAppsReads,
    OAuthAppsWrites,
    TemplateSourcesReads,
    TemplateSourcesWrites,
)
from app.services.integrations.hosts.directory_reads import HostsReads
from app.services.integrations.hosts.directory_writes import HostsWrites


class IntegrationsDirectory(
    HostsWrites,
    OAuthAppsWrites,
    TemplateSourcesWrites,
    HostsReads,
    OAuthAppsReads,
    TemplateSourcesReads,
):
    pass


__all__ = ["IntegrationsDirectory"]
