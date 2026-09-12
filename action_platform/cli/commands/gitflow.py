"""`action-platform gitflow` command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from action_platform.core import gitflow
from action_platform.core.exception import ActionPlatformError

console = Console()


def run(
    since: str | None = typer.Option(
        None,
        "--since",
        help="Check commits after this ref (default: merge base with develop/main)",
    ),
    install: bool = typer.Option(
        False, "--install-hooks", help="Point core.hooksPath at .githooks and exit"
    ),
) -> None:
    """Check the current branch and commits against git-flow and Conventional Commits."""
    cwd = Path.cwd()

    if install:
        if gitflow.install_hooks(cwd):
            console.print("[green]hooks installed[/green] (.githooks)")
            return
        raise ActionPlatformError("no .githooks directory or not a git repository")

    report = gitflow.audit(cwd, since=since)
    console.print(
        f"branch [bold]{report.branch}[/bold], {report.checked_commits} commit(s) checked"
    )

    if report.ok:
        console.print("[green]git-flow ok[/green]")
        return

    for problem in report.problems:
        console.print(f"[red]✗[/red] {problem}")

    raise typer.Exit(code=1)
