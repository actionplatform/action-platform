"""Typer app assembly."""

import typer

from devtool.cli.commands import deploy as deploy_cmd
from devtool.cli.commands import init as init_cmd
from devtool.cli.commands import release as release_cmd

app = typer.Typer(
    name="devtool",
    help="Standardize init, release, and deploy across any stack.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

app.command("init")(init_cmd.run)
app.command("release")(release_cmd.run)
app.command("deploy")(deploy_cmd.run)
