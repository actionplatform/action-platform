"""`action-platform service` commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from action_platform.core.generate import apply_service
from action_platform.core.templates import load_matrix
from action_platform.logging import logger

app = typer.Typer(
    help="Add application dependencies (database, cache, storage) to a project.",
    no_args_is_help=True,
)
console = Console()


@app.command("add")
def add(
    name: str = typer.Argument(..., help="postgres, redis, s3, ..."),
    provider: str | None = typer.Option(
        None, "--provider", help="docker, aws-rds, aws, ... (default: first listed)"
    ),
    project: Path = typer.Option(
        None, "--project", "-p", help="Project directory (default: cwd)"
    ),
    update: bool = typer.Option(False, "--update", help="Refresh the templates cache"),
) -> None:
    """Add services/<name>/ with up + link scripts and record it in platform.toml."""
    repo, matrix = load_matrix(update=update)
    target = (project or Path.cwd()).resolve()

    apply_service(repo, matrix.service(name), target, provider=provider)

    logger.info("added service %s to %s", name, target)


@app.command("list")
def list_() -> None:
    """List available services and their providers."""
    _, matrix = load_matrix()

    for service in matrix.services:
        console.print(
            f"[bold]{service.name}[/bold]  {service.description}  "
            f"[dim]({', '.join(service.providers)})[/dim]"
        )
