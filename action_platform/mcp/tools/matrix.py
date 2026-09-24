"""What can be generated: projects, clouds, services."""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import Field

from action_platform.core.scaffold.catalog import load_matrix
from action_platform.mcp import schemas
from action_platform.mcp.annotations import READ_ONLY, tool


def register(mcp: Any) -> None:
    @tool(mcp, annotations=READ_ONLY)
    def list_matrix(
        source: Annotated[
            Optional[str],
            Field(
                description="Another templates repository as url[@ref]; default is the official actionplatform/templates at v1"
            ),
        ] = None,
    ) -> schemas.Matrix:
        """Projects (type/stack/template), clouds and services available to generate.

        Start here. `default` marks the template `init_project` picks when
        none is given; a cloud lists the `types` and `languages` it accepts.
        Pass `source` to read a custom templates repository instead of the
        official one; the same value then goes to init_project, cloud_set
        and service_add.
        """
        _, matrix = load_matrix(source=source)

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
