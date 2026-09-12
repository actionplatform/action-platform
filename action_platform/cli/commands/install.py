"""`action-platform install` command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from action_platform.core import install as installing

console = Console()


def run(
    type_: str = typer.Option("web", "--type", help="web, library, docs, plugin"),
    language: str | None = typer.Option(
        None, "--language", help="python, go, node, php, java, rust (default: detected)"
    ),
    ci: str = typer.Option("github", "--ci", help="github, gitlab, jenkins"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be created"),
) -> None:
    """Install the platform in this repository: platform.toml, hooks, code quality, CI. Never overwrites."""
    plan = installing.install(
        Path.cwd(), type_=type_, language=language, ci=ci, dry_run=dry_run
    )
    verb = "would create" if dry_run else "created"
    console.print(
        f"[bold]{plan.root.name}[/bold] — {plan.language} {plan.type}, ci {plan.ci}"
    )

    for rel in plan.created:
        console.print(f"  [green]+[/green] {rel}  ({verb})")

    for rel in plan.skipped:
        console.print(f"  [dim]= {rel}  (exists, kept)[/dim]")

    if plan.hooks_installed:
        console.print("  [green]✓[/green] git hooks installed (.githooks)")

    if not dry_run:
        console.print(
            "\nnext: review platform.toml, commit on a branch "
            "(action-platform branch chore platform), then action-platform gitflow"
        )
