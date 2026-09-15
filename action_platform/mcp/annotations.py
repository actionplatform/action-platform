"""Tool hints, so a client can ask the human before anything irreversible, and the decorator every tool registers through."""

from __future__ import annotations

import functools
from typing import Any, Callable

from action_platform.core.exception import ActionPlatformError

try:
    from mcp.server.mcpserver.exceptions import ToolError
    from mcp.types import ToolAnnotations
except ImportError:

    class ToolAnnotations:
        """Stands in when the mcp extra is absent — a plugin module can still import its hints; only serving needs the SDK."""

        def __init__(self, **hints: Any) -> None:
            self.__dict__.update(hints)

    ToolError = ActionPlatformError

READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)

WRITES_LOCAL = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)

REACHES_OUT = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=True,
)

DESTRUCTIVE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=False,
    open_world_hint=True,
)


def tool(mcp: Any, **options: Any) -> Callable:
    """`@tool(mcp, annotations=...)`: registers the function as an MCP tool whose platform errors — a refused permission, an unknown app, a git-flow violation — reach the model as the tool's error text instead of a bare `Error executing tool`."""

    def decorate(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def guarded(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except ActionPlatformError as e:
                raise ToolError(str(e)) from e

        return mcp.tool(**options)(guarded)

    return decorate
