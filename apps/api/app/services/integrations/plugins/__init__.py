"""Plugins on the hosted platform: what the image bundles, and the database-backed options store."""

from app.services.integrations.plugins.manager import PluginManager
from app.services.integrations.plugins.options import DbOptions

__all__ = ["DbOptions", "PluginManager"]
