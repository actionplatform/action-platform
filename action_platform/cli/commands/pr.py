"""`action-platform pr` command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from action_platform.core.flow import pullrequest

console = Console()


def run(
    base: str | None = typer.Option(
        None, "--base", help="Target branch (default from git-flow)"
    ),
    title: str | None = typer.Option(
        None, "--title", help="Default: first commit on the branch"
    ),
    body: str | None = typer.Option(
        None, "--body", help="Default: commits grouped by type"
    ),
    draft: bool = typer.Option(False, "--draft"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show target, title and body; open nothing"
    ),
) -> None:
    """Open a pull request for the current branch: audits git-flow, picks the target, describes the commits."""
    cwd = Path.cwd()

    if dry_run:
        proposal = pullrequest.propose(cwd, base=base, title=title)
        console.print(f"[bold]{proposal.head}[/bold] → [bold]{proposal.base}[/bold]")
        console.print(f"title: {proposal.title}\n")
        console.print(body or proposal.body)
        return

    ref = pullrequest.open_pr(cwd, base=base, title=title, body=body, draft=draft)
    console.print(f"[green]opened[/green] #{ref.number} {ref.url}")
