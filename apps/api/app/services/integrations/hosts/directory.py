"""The integrations an organization connected, on one session: code hosts (their tokens refreshed through the providers), CI servers, OAuth apps, template sources."""

from app.repositories.integrations import (
    CiHostsReads,
    CiHostsWrites,
    HostsWrites,
    OAuthAppsReads,
    OAuthAppsWrites,
    TemplateSourcesReads,
    TemplateSourcesWrites,
)
from app.services.integrations.hosts.credentials import FreshCredentials


class IntegrationsDirectory(
    FreshCredentials,
    HostsWrites,
    CiHostsWrites,
    OAuthAppsWrites,
    TemplateSourcesWrites,
    CiHostsReads,
    OAuthAppsReads,
    TemplateSourcesReads,
):
    pass


__all__ = ["IntegrationsDirectory"]
