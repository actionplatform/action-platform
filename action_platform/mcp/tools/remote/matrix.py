"""What the platform can generate: project types, stacks, templates, clouds and services."""

from __future__ import annotations

from typing import Any

from action_platform.mcp import schemas
from action_platform.mcp.annotations import READ_ONLY, tool
from action_platform.remote.client import Remote


def register(mcp: Any, remote: Remote) -> None:
    @tool(mcp, annotations=READ_ONLY)
    def list_matrix() -> schemas.Matrix:
        """Project types, stacks, templates, clouds and services the platform can generate.

        Merges the official repository with every template repository the
        organization added; each entry carries its `source`, and `sources`
        lists them with their status. Pass a custom source's name to
        init_app, set_cloud and add_service.
        """
        return remote.matrix()
