"""Typer app assembly."""

import sys

import typer

from action_platform.core.exception import ActionPlatformError
from app.core.cli import db as db_cmd
from app.core.cli import serve as serve_cmd
from app.core.cli import worker as worker_cmd

app = typer.Typer(
    name="action-platform-api",
    help="The hosted Action Platform: API server, job worker and database.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

app.command("serve")(serve_cmd.run)
app.command("worker")(worker_cmd.run)
app.add_typer(db_cmd.app, name="db")


def main() -> None:
    try:
        app()
    except ActionPlatformError as e:
        typer.echo(f"error: {e}", err=True)
        sys.exit(1)
