"""Plugins on the hosted platform: install, switch, restart; the database-backed options store."""

from app.services.plugins.manager import (
    INSTALL,
    REMOVE,
    RESTART,
    PluginManager,
    exit_soon,
)
from app.services.plugins.options import DbOptions

__all__ = ["DbOptions", "INSTALL", "PluginManager", "REMOVE", "RESTART", "exit_soon"]
