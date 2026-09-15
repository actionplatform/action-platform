"""`action-platform branch` command."""

from __future__ import annotations

from pathlib import Path

import typer

from action_platform.core.wiring import wired
from action_platform.core.flow import gitflow
from action_platform.logging import logger


def run(
    kind: str = typer.Argument(
        ...,
        help="feature | bugfix | hotfix | release | "
        + " | ".join(
            k
            for k in sorted(gitflow.current().kinds)
            if k not in {"feature", "bugfix", "hotfix", "release"}
        ),
    ),
    code: str = typer.Argument(
        ..., help="Issue or ticket code: 42, PROJ-123, 1.4.0 for release"
    ),
    slug: str | None = typer.Argument(None, help="Optional words appended as a slug"),
    push: bool = typer.Option(
        True, "--push/--no-push", help="Push the new branch upstream"
    ),
) -> None:
    """Start a branch: checkout the right base (develop or main), pull, create <kind>/<code>."""
    branch = wired.gitflow(Path.cwd()).start(kind, code, slug, push=push)
    logger.info(
        "on %s (from %s)%s",
        branch.name,
        branch.base,
        " — pushed" if branch.pushed else "",
    )
