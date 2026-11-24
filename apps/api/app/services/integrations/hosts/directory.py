"""The integrations an organization connected, on one session: code hosts and services (their tokens refreshed through the providers), CI servers, OAuth apps, template sources."""

from app.repositories.integrations import (
    CiHostsReads,
    CiHostsWrites,
    ConnectionsWrites,
    HostsWrites,
    OAuthAppsReads,
    OAuthAppsWrites,
    TemplateSourcesReads,
    TemplateSourcesWrites,
)
from app.services.integrations.connections.credentials import FreshConnections
from app.services.integrations.hosts.credentials import FreshCredentials


class IntegrationsDirectory(
    FreshCredentials,
    FreshConnections,
    HostsWrites,
    ConnectionsWrites,
    CiHostsWrites,
    OAuthAppsWrites,
    TemplateSourcesWrites,
    CiHostsReads,
    OAuthAppsReads,
    TemplateSourcesReads,
):
    pass


__all__ = ["IntegrationsDirectory"]
