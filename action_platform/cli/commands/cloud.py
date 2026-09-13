"""`action-platform cloud` commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from action_platform.core.manifest import Manifest
from action_platform.core.scaffold.generate import apply_cloud
from action_platform.core.scaffold.templates import load_matrix
from action_platform.logging import logger

app = typer.Typer(
    help="Apply deploy overlays to an existing project.", no_args_is_help=True
)
console = Console()


@app.command("set")
def set_(
    name: str = typer.Argument(..., help="aws/lambda, docker, ..."),
    project: Path = typer.Option(
        None, "--project", "-p", help="Project directory (default: cwd)"
    ),
    update: bool = typer.Option(False, "--update", help="Refresh the templates cache"),
    source: str | None = typer.Option(
        None,
        "--source",
        help="Another templates repository, url[@ref]; default is the official one",
    ),
) -> None:
    """Apply a cloud overlay and set [deploy] target in platform.toml (replaces the previous one)."""
    repo, matrix = load_matrix(update=update, source=source)
    target = (project or Path.cwd()).resolve()

    apply_cloud(repo, matrix.cloud(name), target)

    logger.info("applied cloud %s to %s", name, target)


@app.command("list")
def list_(
    project: Path = typer.Option(
        None, "--project", "-p", help="Filter by what this project supports"
    ),
) -> None:
    """List cloud overlays, optionally only those compatible with a project."""
    _, matrix = load_matrix()
    clouds = matrix.clouds

    if project is not None:
        meta = Manifest.of(project.resolve()).project
        clouds = matrix.clouds_for(meta.get("type", ""), meta.get("language", ""))

    for cloud in clouds:
        console.print(f"[bold]{cloud.name}[/bold]  {cloud.description}")
