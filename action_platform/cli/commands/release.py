"""`action-platform release` command."""

from __future__ import annotations

from pathlib import Path

import typer

from action_platform.core.config import Config
from action_platform.core.action_platform import ActionPlatform
from action_platform.logging import logger


def run(
    level: str = typer.Argument("patch", help="patch | minor | major | X.Y.Z"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Bump version, generate changelog, tag, and publish release."""
    config = Config.from_toml(Path.cwd() / "platform.toml")
    tool = ActionPlatform(config=config)
    ctx = tool.release(level=level, dry_run=dry_run)
    logger.info("release done: %s", ctx.next_version)
