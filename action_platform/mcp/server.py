"""Builds the MCP server and runs it over the chosen transport."""

from __future__ import annotations

import argparse
from typing import Optional

from mcp.server.mcpserver import MCPServer

from action_platform import __version__
from action_platform.mcp import prompts
from action_platform.mcp.tools import flow, lifecycle, matrix, project

INSTRUCTIONS = """Scaffold, deploy and operate projects on the Action Platform.

Start with list_matrix to learn the project types, stacks, templates,
clouds and services that exist; pass `source` (url[@ref]) to read a custom
templates repository instead of the official one. init_project generates a
new project; install_platform brings an existing repository in. Both work
locally; nothing reaches a remote host until push_project, which creates a
repository visible to others — confirm with the user before calling it.

Every project follows git-flow: work happens on <kind>/<code> branches
started with start_branch, never directly on main or develop. Finish with
propose_pull_request (preview) and open_pull_request (on approval);
gitflow_rules explains the rules when in doubt.

release and deploy default to dry runs: show the user what would happen,
then call again with dry_run=false. rollback changes what is live; ask first."""

REMOTE_INSTRUCTIONS = """Operate apps on a hosted Action Platform.

These tools act on the platform the CLI is logged in to (`action-platform
login <server>`), not on files on this machine, and with the role the
account has in its organization (viewer, developer, deployer, admin, owner):
a refused call names the missing permission. Start with whoami and
list_apps. Every app is a repository the platform has cloned:
sync_app before auditing, editing or releasing so the clone is current.

Work follows git-flow: start_branch, then write_manifest / set_cloud /
add_service, then commit_changes (which can create the branch and open the
pull request in one call), or propose_pull_request + open_pull_request.
Protected branches refuse direct commits.

release and deploy default to dry runs: show the user what would happen,
then call again with dry_run=false. Stable versions come only from
main/master; pass `branch` to release from another branch. remove_app
deletes the platform's clone; ask first."""


def build(remote: Optional[str] = None) -> MCPServer:
    """Assemble the server. Local: tools call the core modules directly — same code path as the CLI.
    Remote: tools call a hosted platform with the token from `action-platform login`."""
    if remote is not None:
        from action_platform.mcp.tools import remote as remote_tools
        from action_platform.remote.client import Remote

        client = Remote.from_credentials(remote or None)
        mcp = MCPServer(
            "action-platform", instructions=REMOTE_INSTRUCTIONS, version=__version__
        )
        remote_tools.register(mcp, client)
        flow.register_rules(mcp)

        return mcp

    mcp = MCPServer("action-platform", instructions=INSTRUCTIONS, version=__version__)

    matrix.register(mcp)
    project.register(mcp)
    flow.register(mcp)
    lifecycle.register(mcp)
    prompts.register(mcp)

    return mcp


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="action-platform-mcp",
        description="Expose the Action Platform as MCP tools.",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Serve streamable HTTP on --host/--port instead of stdio.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--remote",
        nargs="?",
        const="",
        default=None,
        metavar="SERVER",
        help="Act on the hosted platform from `action-platform login` (optionally which one) instead of local files.",
    )

    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    mcp = build(remote=args.remote)

    if args.http:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
        return

    mcp.run()


if __name__ == "__main__":
    main()
