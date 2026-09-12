"""MCP (Model Context Protocol) server built on top of the platform core.

Requires the ``mcp`` extra::

    pip install action-platform[mcp]
    action-platform-mcp
"""

from action_platform.mcp.server import build, main

__all__ = ["build", "main"]
