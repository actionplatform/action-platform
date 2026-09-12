"""`action-platform deploy` command."""

from __future__ import annotations

from pathlib import Path

import typer

from action_platform.core.config import Config
from action_platform.core.action_platform import ActionPlatform
from action_platform.logging import logger


def run(
    target: str = typer.Option(None, "--target", help="Deploy target name (dokploy, pypi, ...)"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Publish artifacts or promote application via configured targets."""
    config = Config.from_toml(Path.cwd() / "platform.toml")
    tool = ActionPlatform(config=config)
    results = tool.deploy(target=target, dry_run=dry_run)
    for r in results:
        logger.info("deploy %s ok=%s version=%s", r.target, r.ok, r.version)
