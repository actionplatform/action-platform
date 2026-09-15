"""MCP (Model Context Protocol) server built on top of the platform core.

Serving requires the ``mcp`` extra::

    pip install action-platform[mcp]
    action-platform-mcp

Without it the package still imports — plugins declare their tools through
``action_platform.mcp.annotations`` on any install — but ``build`` and
``main`` are None.
"""

try:
    from action_platform.mcp.server import build, main
except ImportError:
    build = None
    main = None

__all__ = ["build", "main"]
