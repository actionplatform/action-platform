"""Typer app assembly."""

import typer

from action_platform.cli.commands import branch as branch_cmd
from action_platform.cli.commands import cloud as cloud_cmd
from action_platform.cli.commands import deploy as deploy_cmd
from action_platform.cli.commands import gitflow as gitflow_cmd
from action_platform.cli.commands import init as init_cmd
from action_platform.cli.commands import mcp as mcp_cmd
from action_platform.cli.commands import plugin as plugin_cmd
from action_platform.cli.commands import pr as pr_cmd
from action_platform.cli.commands import install as install_cmd
from action_platform.cli.commands import login as login_cmd
from action_platform.cli.commands import release as release_cmd
from action_platform.cli.commands import service as service_cmd
from action_platform.plugins import registry

app = typer.Typer(
    name="action-platform",
    help="Standardize init, release, and deploy across any stack.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

app.command("init")(init_cmd.run)
app.command("install")(install_cmd.run)
app.command("branch")(branch_cmd.run)
app.command("gitflow")(gitflow_cmd.run)
app.command("gitflow-check", hidden=True)(gitflow_cmd.check)
app.command("pr")(pr_cmd.run)
app.command("release")(release_cmd.run)
app.command("deploy")(deploy_cmd.run)
app.command("rollback")(deploy_cmd.rollback)
app.command("diagnose")(deploy_cmd.diagnose)
app.command("readiness")(deploy_cmd.readiness)
app.command("scopes")(deploy_cmd.scopes)
app.command("logs")(deploy_cmd.logs)
app.command("destroy")(deploy_cmd.destroy)
app.command("deployments")(deploy_cmd.deployments)
app.command("deploy-record")(deploy_cmd.record)
app.command("mcp")(mcp_cmd.run)
app.command("login")(login_cmd.login)
app.command("logout")(login_cmd.logout)
app.command("whoami")(login_cmd.whoami)
app.add_typer(cloud_cmd.app, name="cloud")
app.add_typer(service_cmd.app, name="service")
app.add_typer(plugin_cmd.app, name="plugin")
registry.installed().register(None, app)
