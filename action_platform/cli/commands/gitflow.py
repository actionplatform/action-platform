"""`action-platform gitflow` command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from action_platform.core.flow import gitflow
from action_platform.core.wiring import wired
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
        report = wired.gitflow(cwd).install_hooks()

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

    report = wired.gitflow(cwd).audit(since=since)
    console.print(
        f"branch [bold]{report.branch}[/bold], {report.checked_commits} commit(s) checked"
    )

    if report.ok:
        console.print("[green]git-flow ok[/green]")
        return

    for problem in report.problems:
        console.print(f"[red]✗[/red] {problem}")

    raise typer.Exit(code=1)


def check(
    what: str = typer.Argument(..., help="branch, commit-msg or protect"),
    values: list[str] = typer.Argument(
        None,
        help="The branch name, the message or its file, the branch and the message",
    ),
) -> None:
    """One git-flow rule, the way the git hooks ask it — through the core, so a plugin that changed the rules is obeyed."""
    values = list(values or [])
    rules = gitflow.current()

    if what == "branch":
        problem = rules.check_branch(values[0] if values else "")
    elif what == "commit-msg":
        message = values[0] if values else ""
        source = Path(message)

        if source.is_file():
            message = source.read_text().splitlines()[0] if source.read_text() else ""

        problem = rules.check_commit(message)
    elif what == "protect":
        problem = rules.check_protected(
            values[0] if values else "", values[1] if len(values) > 1 else ""
        )
    else:
        raise ActionPlatformError(
            f"unknown check {what!r}: branch, commit-msg or protect"
        )

    if problem:
        typer.echo(f"::error::{problem}", err=True)

        raise typer.Exit(code=1)
