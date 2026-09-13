"""`action-platform gitflow` command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from action_platform.core.flow.workflow import GitFlow
from action_platform.core.exception import ActionPlatformError

console = Console()


def run(
    since: str | None = typer.Option(
        None,
        "--since",
        help="Check commits after this ref (default: merge base with develop/main)",
    ),
    install: bool = typer.Option(
        False,
        "--install-hooks",
        help="Install the bundled git hooks into .git/hooks and exit",
    ),
) -> None:
    """Check the current branch and commits against git-flow and Conventional Commits."""
    cwd = Path.cwd()

    if install:
        report = GitFlow(cwd).install_hooks()

        if report:
            console.print(f"[green]hooks installed[/green] ({report.directory})")

            for name in report.preserved:
                console.print(
                    f"  kept your {name} as {name}.pre-action-platform; it still runs after ours"
                )
        elif report.skipped:
            console.print(f"[yellow]{report.skipped}[/yellow]")
            return
        raise ActionPlatformError("not a git repository")

    report = GitFlow(cwd).audit(since=since)
    console.print(
        f"branch [bold]{report.branch}[/bold], {report.checked_commits} commit(s) checked"
    )

    if report.ok:
        console.print("[green]git-flow ok[/green]")
        return

    for problem in report.problems:
        console.print(f"[red]✗[/red] {problem}")

    raise typer.Exit(code=1)
