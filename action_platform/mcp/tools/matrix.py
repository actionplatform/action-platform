"""What can be generated: projects, clouds, services."""

from __future__ import annotations

from typing import Any

from action_platform.core.templates import load_matrix
from action_platform.mcp.annotations import READ_ONLY


def register(mcp: Any) -> None:
    @mcp.tool(annotations=READ_ONLY)
    def list_matrix() -> dict:
        """Projects (type/stack/template), clouds and services available to generate.

        Start here. `default` marks the template `init_project` picks when
        none is given; a cloud lists the `types` and `languages` it accepts.
        """
        _, matrix = load_matrix()

        return {
            "projects": [
                {
                    "type": leaf.type,
                    "stack": leaf.stack,
                    "template": leaf.template,
                    "default": leaf.default,
                    "description": leaf.description,
                }
                for leaf in matrix.leaves
            ],
            "clouds": [
                {
                    "name": c.name,
                    "types": c.types,
                    "languages": c.languages,
                    "description": c.description,
                }
                for c in matrix.clouds
            ],
            "services": [
                {
                    "name": s.name,
                    "providers": s.providers,
                    "description": s.description,
                }
                for s in matrix.services
            ],
        }
