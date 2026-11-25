"""`action-platform protection …` — git-flow enforced on an app's code host, through the platform the CLI is logged in to; JSON on stdout."""

from __future__ import annotations

from typing import Optional

import typer
from pydantic import BaseModel

from action_platform.mcp.tools.remote.common import app_in_project, org_of
from action_platform.remote.client import Remote

app = typer.Typer(
    help="Branch protection on the code host: what it enforces, and applying the git-flow rules.",
    no_args_is_help=True,
)


def _print(model: BaseModel) -> None:
    typer.echo(model.model_dump_json(indent=2, exclude_none=True))


@app.command("status")
def status(
    id: str = typer.Argument(..., help="App id from the platform's app list"),
    refresh: bool = typer.Option(False, help="Read the code host now"),
) -> None:
    """Each rule: native, check-based or inactive, with the reason."""
    remote = Remote.from_credentials()
    project, row = app_in_project(remote, id)
    _print(remote.protection(project.id, row.id, refresh, org_of(project)))


@app.command("apply")
def apply(
    id: str = typer.Argument(..., help="App id from the platform's app list"),
    enforce: Optional[bool] = typer.Option(
        None,
        "--enforce/--no-enforce",
        help="Keep the rules enforced (reapplied on drift), or stop; omitted applies once",
    ),
) -> None:
    """Apply the git-flow rules to the app's protected branches on the code host."""
    remote = Remote.from_credentials()
    project, row = app_in_project(remote, id)
    organization = org_of(project)

    if enforce is not None:
        remote.set_protection(project.id, row.id, enforce, organization)

        if not enforce:
            _print(remote.protection(project.id, row.id, False, organization))

            return

    _print(remote.apply_protection(project.id, row.id, organization))
