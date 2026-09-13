"""Create and shape a project: init, cloud overlay, services, platform.toml."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Optional

from pydantic import Field

from action_platform.core.scaffold import install as installing
from action_platform.core.manifest import Manifest
from action_platform.core.scaffold.generate import (
    apply_cloud,
    apply_service,
    generate_project,
    push_project,
)
from action_platform.core.scaffold.templates import load_matrix
from action_platform.mcp.annotations import READ_ONLY, REACHES_OUT, WRITES_LOCAL

ProjectDir = Annotated[
    Optional[str], Field(description="Project directory; default is the cwd.")
]


TemplateSourceArg = Annotated[
    Optional[str],
    Field(
        description="Templates repository as url[@ref]; default is the official one. Use the same value given to list_matrix."
    ),
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
        ci: Annotated[
            str, Field(description="github, gitlab, jenkins or bitbucket")
        ] = "github",
        cloud: Annotated[
            Optional[str],
            Field(description="Deploy overlay: aws/lambda, aws/amplify, docker"),
        ] = None,
        output: Annotated[
            Optional[str], Field(description="Parent directory; default is the cwd.")
        ] = None,
        source: TemplateSourceArg = None,
    ) -> dict:
        """Generate a project from the templates matrix, optionally with a cloud overlay.

        Nothing leaves the machine: use `push_project` afterwards to create
        the remote repository. Call `list_matrix` first when unsure of the
        type, stack or template names.
        """
        repo, matrix = load_matrix(source=source)
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
        source: TemplateSourceArg = None,
    ) -> dict:
        """Apply a deploy overlay to an existing project and set [deploy] target in platform.toml.

        Replaces the previous target. The overlay refuses a project whose
        type or language it does not support.
        """
        repo, matrix = load_matrix(source=source)
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
        source: TemplateSourceArg = None,
    ) -> dict:
        """Add a dependency as services/<name>/ with `up` (provision) and `link` (env vars) scripts."""
        repo, matrix = load_matrix(source=source)
        root = _root(project)
        apply_service(repo, matrix.service(service), root, provider=provider)

        return {"path": str(root / "services" / service), "provider": provider}

    @mcp.tool(annotations=WRITES_LOCAL)
    def install_platform(
        project: ProjectDir = None,
        type: Annotated[str, Field(description="web, library, docs, plugin")] = "web",
        language: Annotated[
            Optional[str],
            Field(
                description="python, go, node, php, java, rust; default detected from the repo"
            ),
        ] = None,
        ci: Annotated[
            str, Field(description="github, gitlab, jenkins or bitbucket")
        ] = "github",
        dry_run: Annotated[
            bool, Field(description="true only reports what would be created")
        ] = True,
    ) -> dict:
        """Install the platform in an existing repository: platform.toml, .code_quality, CI checks, AGENTS.md, and git hooks into .git/hooks.

        Never overwrites a file that exists. Defaults to a dry run — show the
        plan, then call again with dry_run=false. App code and existing deploy
        files are not touched.
        """
        plan = installing.install(
            _root(project), type_=type, language=language, ci=ci, dry_run=dry_run
        )

        return {
            "path": str(plan.root),
            "language": plan.language,
            "type": plan.type,
            "ci": plan.ci,
            "created": plan.created,
            "kept": plan.skipped,
            "hooks_installed": plan.hooks_installed,
            "hooks_preserved": plan.hooks_preserved,
            "hooks_skipped": plan.hooks_skipped,
            "dry_run": dry_run,
        }

    @mcp.tool(annotations=READ_ONLY)
    def project_info(project: ProjectDir = None) -> dict:
        """Read platform.toml: name, type, stack, language, deploy target, services."""
        return Manifest.of(_root(project)).project
