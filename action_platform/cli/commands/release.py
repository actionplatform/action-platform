"""`action-platform release` command."""

from __future__ import annotations

import typer

from action_platform.bootstrap import project
from action_platform.logging import logger


def run(
    level: str = typer.Argument("patch", help="patch | minor | major | X.Y.Z"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    rc: bool | None = typer.Option(
        None,
        "--rc/--stable",
        help="Pre-release X.Y.Z-rc.N (default: rc off main/master, stable on them)",
    ),
    component: str | None = typer.Option(
        None,
        "--component",
        "-c",
        help="Release one [components.<name>] of platform.toml (tag <name>/vX.Y.Z) instead of the repository",
    ),
) -> None:
    """Bump version, generate changelog, tag, and publish release. Off main/master it cuts an rc."""
    ctx = project().release(
        level=level, dry_run=dry_run, prerelease=rc, component=component
    )
    logger.info("release done: %s", ctx.next_version)
