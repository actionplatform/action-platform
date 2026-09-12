"""`action-platform deploy | rollback | diagnose | destroy` commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from action_platform.core.action_platform import ActionPlatform
from action_platform.core.config import Config
from action_platform.core.exception import DeployError
from action_platform.logging import logger
from action_platform.settings import settings

console = Console()

TARGET = typer.Option(
    None, "--target", help="Filter by target name (aws/lambda, docker, ...)"
)
STAGE = typer.Option(
    None, "--stage", help="dev | prod (default: prod on main/master, else dev)"
)


def _tool() -> ActionPlatform:
    return ActionPlatform(config=Config.from_toml(Path.cwd() / settings.CONFIG_FILE))


def run(
    target: str | None = TARGET,
    stage: str | None = STAGE,
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Ship the current version to the [deploy] target in platform.toml."""
    for r in _tool().deploy(target=target, dry_run=dry_run, stage=stage):
        logger.info(
            "deploy %s ok=%s version=%s url=%s", r.target, r.ok, r.version, r.url
        )

        if not r.ok:
            raise DeployError(r.error or f"{r.target} failed")


def rollback(
    to_version: str | None = typer.Argument(
        None, help="Version to return to (default: previous)"
    ),
    target: str | None = TARGET,
    stage: str | None = STAGE,
) -> None:
    """Return the target to a previous version."""
    try:
        _tool().rollback(target=target, to_version=to_version, stage=stage)
    except NotImplementedError as e:
        raise DeployError(str(e)) from e
    logger.info("rollback done")


def diagnose(target: str | None = TARGET, stage: str | None = STAGE) -> None:
    """Health, status and URL of the deployed target."""
    try:
        results = _tool().diagnose(target=target, stage=stage)
    except NotImplementedError as e:
        raise DeployError(str(e)) from e
    for d in results:
        mark = "[green]ok[/green]" if d.ok else "[red]not ok[/red]"
        console.print(f"[bold]{d.target}[/bold] {mark} {d.status}")

        if d.url:
            console.print(f"  url: {d.url}")

        for k, v in d.details.items():
            console.print(f"  {k}: {v}")


def destroy(
    target: str | None = TARGET,
    stage: str | None = STAGE,
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Tear the target down. Irreversible."""
    if not yes and not typer.confirm("Delete the deployed target?"):
        raise typer.Abort()

    try:
        _tool().destroy(target=target, stage=stage)
    except NotImplementedError as e:
        raise DeployError(str(e)) from e
    logger.info("destroy done")
