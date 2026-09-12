"""Builds the MCP server and runs it over the chosen transport."""

from __future__ import annotations

import argparse
from typing import Optional

from mcp.server.mcpserver import MCPServer

from action_platform import __version__
from action_platform.mcp.tools import lifecycle, matrix, project

INSTRUCTIONS = """Scaffold, deploy and operate projects on the Action Platform.

Start with list_matrix to learn the project types, stacks, templates,
clouds and services that exist. init_project generates locally; nothing
reaches a remote host until push_project, which creates a repository
visible to others — confirm with the user before calling it.

release and deploy default to dry runs: show the user what would happen,
then call again with dry_run=false. rollback changes what is live; ask first."""


def build() -> MCPServer:
    """Assemble the server. Tools call the core modules directly — same code path as the CLI."""
    mcp = MCPServer("action-platform", instructions=INSTRUCTIONS, version=__version__)

    matrix.register(mcp)
    project.register(mcp)
    lifecycle.register(mcp)

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

    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    mcp = build()

    if args.http:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
        return

    mcp.run()


if __name__ == "__main__":
    main()
