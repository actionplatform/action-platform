"""`action-platform install` command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from action_platform.core.scaffold import install as installing

console = Console()


def run(
    type_: str = typer.Option("web", "--type", help="web, library, docs, plugin"),
    language: str | None = typer.Option(
        None,
        "--language",
        help="python, go, node, php, java, rust, ruby (default: detected)",
    ),
    ci: str | None = typer.Option(
        None,
        "--ci",
        help="github, gitlab, jenkins, bitbucket, or none for no pipeline files (default: platform.toml, else from the remote)",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be created"),
) -> None:
    """Install the platform in this repository: platform.toml, code quality, CI files (never overwritten) and git hooks into .git/hooks (always refreshed)."""
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

    for name in plan.hooks_preserved:
        console.print(
            f"  kept your {name} as {name}.pre-action-platform; it still runs after ours"
        )

    if plan.hooks_skipped:
        console.print(f"[yellow]{plan.hooks_skipped}[/yellow]")

    if plan.hooks_installed:
        console.print(
            "  [green]✓[/green] git hooks installed (.git/hooks, unversioned)"
        )

    if dry_run or not plan.created:
        return

    console.print(
        "\nnext: review the files, then "
        '[bold]git add -A && git commit -m "chore(platform): install action-platform"[/bold] '
        "— chore(platform) commits are allowed on main"
    )
