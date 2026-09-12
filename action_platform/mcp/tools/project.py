"""Create and shape a project: init, cloud overlay, services, platform.toml."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Optional

from pydantic import Field

from action_platform.core.generate import (
    apply_cloud,
    apply_service,
    generate_project,
    push_project,
    read_platform,
)
from action_platform.core.templates import load_matrix
from action_platform.mcp.annotations import READ_ONLY, REACHES_OUT, WRITES_LOCAL

ProjectDir = Annotated[
    Optional[str], Field(description="Project directory; default is the cwd.")
]


def _root(project: Optional[str]) -> Path:
    return Path(project).resolve() if project else Path.cwd()


def register(mcp: Any) -> None:
    @mcp.tool(annotations=WRITES_LOCAL)
    def init_project(
        type: Annotated[str, Field(description="web, library, docs, plugin, empty")],
        name: Annotated[str, Field(description="Human name; the slug is derived.")],
        stack: Optional[str] = None,
        template: Optional[str] = None,
        ci: Annotated[str, Field(description="github, gitlab or jenkins")] = "github",
        cloud: Annotated[
            Optional[str],
            Field(description="Deploy overlay: aws/lambda, aws/amplify, docker"),
        ] = None,
        output: Annotated[
            Optional[str], Field(description="Parent directory; default is the cwd.")
        ] = None,
    ) -> dict:
        """Generate a project from the templates matrix, optionally with a cloud overlay.

        Nothing leaves the machine: use `push_project` afterwards to create
        the remote repository. Call `list_matrix` first when unsure of the
        type, stack or template names.
        """
        repo, matrix = load_matrix()
        leaf = matrix.resolve(type, stack, template)
        project = generate_project(repo, leaf, name=name, ci=ci, output=_root(output))
        result = {"path": str(project), "template": leaf.directory}

        if cloud:
            apply_cloud(repo, matrix.cloud(cloud), project)
            result["cloud"] = cloud

        return result

    @mcp.tool(name="push_project", annotations=REACHES_OUT)
    def push(
        project: ProjectDir = None,
        private: bool = False,
    ) -> dict:
        """Create the remote repository through [source_host] and push the first commit.

        Creates a public repository on the host unless `private` is true.
        Confirm with the user before calling: it is visible to others once done.
        """
        return {"remote": push_project(_root(project), private=private)}

    @mcp.tool(annotations=WRITES_LOCAL)
    def cloud_set(
        cloud: Annotated[str, Field(description="aws/lambda, aws/amplify, docker")],
        project: ProjectDir = None,
    ) -> dict:
        """Apply a deploy overlay to an existing project and set [deploy] target in platform.toml.

        Replaces the previous target. The overlay refuses a project whose
        type or language it does not support.
        """
        repo, matrix = load_matrix()
        root = _root(project)
        apply_cloud(repo, matrix.cloud(cloud), root)

        return {"path": str(root), "deploy_target": cloud}

    @mcp.tool(annotations=WRITES_LOCAL)
    def service_add(
        service: Annotated[str, Field(description="postgres, ...")],
        provider: Annotated[
            Optional[str],
            Field(description="docker, aws-rds, ...; default is the first listed"),
        ] = None,
        project: ProjectDir = None,
    ) -> dict:
        """Add a dependency as services/<name>/ with `up` (provision) and `link` (env vars) scripts."""
        repo, matrix = load_matrix()
        root = _root(project)
        apply_service(repo, matrix.service(service), root, provider=provider)

        return {"path": str(root / "services" / service), "provider": provider}

    @mcp.tool(annotations=READ_ONLY)
    def project_info(project: ProjectDir = None) -> dict:
        """Read platform.toml: name, type, stack, language, deploy target, services."""
        return read_platform(_root(project))
