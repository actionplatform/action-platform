"""Integrations: OAuth apps and template sources — the pure rows; hosts, which resolve credentials through providers, compose these in `services/integrations/hosts/directory`."""

from app.repositories.integrations.ci_hosts import CiHostsReads, CiHostsWrites
from app.repositories.integrations.oauth_apps import OAuthAppsReads, OAuthAppsWrites
from app.repositories.integrations.template_sources import (
    TemplateSourcesReads,
    TemplateSourcesWrites,
)

__all__ = [
    "CiHostsReads",
    "CiHostsWrites",
    "OAuthAppsReads",
    "OAuthAppsWrites",
    "TemplateSourcesReads",
    "TemplateSourcesWrites",
]
