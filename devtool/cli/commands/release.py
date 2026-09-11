"""`devtool release` command."""

from __future__ import annotations

from pathlib import Path

import typer

from devtool.core.config import Config
from devtool.core.devtool import DevTool
from devtool.logging import logger


def run(
    level: str = typer.Argument("patch", help="patch | minor | major | X.Y.Z"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Bump version, generate changelog, tag, and publish release."""
    config = Config.from_toml(Path.cwd() / "devtool.toml")
    tool = DevTool(config=config)
    ctx = tool.release(level=level, dry_run=dry_run)
    logger.info("release done: %s", ctx.next_version)
