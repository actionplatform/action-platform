"""Integrations: code hosts, CI hosts, OAuth apps and template sources — the rows. Refreshing a host token goes through the provider, in `services/integrations/hosts/credentials`."""

from app.repositories.integrations.ci_hosts import CiHostsReads, CiHostsWrites
from app.repositories.integrations.hosts import HostsReads, HostsWrites
from app.repositories.integrations.oauth_apps import OAuthAppsReads, OAuthAppsWrites
from app.repositories.integrations.template_sources import (
    TemplateSourcesReads,
    TemplateSourcesWrites,
)

__all__ = [
    "CiHostsReads",
    "CiHostsWrites",
    "HostsReads",
    "HostsWrites",
    "OAuthAppsReads",
    "OAuthAppsWrites",
    "TemplateSourcesReads",
    "TemplateSourcesWrites",
]
