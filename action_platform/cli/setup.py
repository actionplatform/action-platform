"""Typer app assembly."""

import typer

from action_platform.cli.commands import cloud as cloud_cmd
from action_platform.cli.commands import deploy as deploy_cmd
from action_platform.cli.commands import init as init_cmd
from action_platform.cli.commands import release as release_cmd

app = typer.Typer(
    name="action-platform",
    help="Standardize init, release, and deploy across any stack.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

app.command("init")(init_cmd.run)
app.command("release")(release_cmd.run)
app.command("deploy")(deploy_cmd.run)
app.add_typer(cloud_cmd.app, name="cloud")
