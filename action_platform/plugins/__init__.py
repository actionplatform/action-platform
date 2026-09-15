"""Plugins installed next to the CLI: discovery, on/off state, registration on the MCP server and the CLI, lifecycle hooks."""

from action_platform.plugins.registry import (
    Loaded,
    PluginError,
    Plugins,
    PluginTools,
    Slots,
    installed,
    reset,
    use_options,
)
from action_platform.plugins.options import FileOptions, Options
from action_platform.plugins.state import OFFICIAL_INDEX, Installed, PluginState

__all__ = [
    "FileOptions",
    "Installed",
    "Loaded",
    "OFFICIAL_INDEX",
    "Options",
    "PluginError",
    "PluginState",
    "PluginTools",
    "Plugins",
    "Slots",
    "installed",
    "reset",
    "use_options",
]
