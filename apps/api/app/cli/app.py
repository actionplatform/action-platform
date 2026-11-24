"""Typer app assembly."""

import os
import sys

import typer

from action_platform.core.exception import ActionPlatformError
from action_platform.bootstrap import bootstrap
from action_platform.core.destination import NetworkPolicy, guard_networks
from app import api_version
from app.cli import db as db_cmd
from app.cli import serve as serve_cmd
from app.cli import tokens as tokens_cmd
from app.cli import users as users_cmd
from app.cli import worker as worker_cmd

app = typer.Typer(
    name="action-platform-api",
    help="The hosted Action Platform: API server, job worker, database, users and tokens.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

app.command("serve")(serve_cmd.run)
app.command("worker")(worker_cmd.run)
app.add_typer(db_cmd.app, name="db")
app.add_typer(users_cmd.app, name="users")
app.add_typer(tokens_cmd.app, name="tokens")


def main() -> None:
    bootstrap("api", version=api_version())
    guard_networks(NetworkPolicy.from_env(os.environ))

    try:
        app()
    except ActionPlatformError as e:
        typer.echo(f"error: {e}", err=True)
        sys.exit(1)
