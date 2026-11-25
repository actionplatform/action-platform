"""`action-platform github …` — read-only checks of the repositories of the GitHub organization the platform's GitHub connection manages, through the platform the CLI is logged in to; JSON on stdout."""

from __future__ import annotations

from typing import Optional

import typer
from pydantic import BaseModel

from action_platform.remote.client import Remote

app = typer.Typer(
    help="GitHub: branch protection and settings of the organization's repositories.",
    no_args_is_help=True,
)

Organization = typer.Option(
    None,
    "--organization",
    help="Organization id or slug, for a token that spans every one",
)


def _print(model: BaseModel) -> None:
    typer.echo(model.model_dump_json(indent=2))


@app.command("branch-protection")
def branch_protection(
    repo: Optional[str] = typer.Option(None, help="Only this repository"),
    organization: Optional[str] = Organization,
) -> None:
    """Protection of each repository's default branch."""
    _print(Remote.from_credentials().github_branch_protection(repo, organization))


@app.command("repo-settings")
def repo_settings(
    repo: Optional[str] = typer.Option(None, help="Only this repository"),
    organization: Optional[str] = Organization,
) -> None:
    """Settings of each repository."""
    _print(Remote.from_credentials().github_repo_settings(repo, organization))
