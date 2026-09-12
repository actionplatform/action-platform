"""`action-platform mcp` command."""

from __future__ import annotations

import typer

from action_platform.core.exception import ActionPlatformError


def run(
    http: bool = typer.Option(
        False, "--http", help="Serve over streamable HTTP instead of stdio"
    ),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8765, "--port", help="Port for --http"),
    remote: bool = typer.Option(
        False,
        "--remote",
        help="Act on the hosted platform from `action-platform login`, not on local files",
    ),
) -> None:
    """Run the embedded MCP server so AI agents can scaffold, deploy and operate projects."""
    try:
        from action_platform.mcp.server import main
    except ModuleNotFoundError as e:
        raise ActionPlatformError(
            "MCP support is not installed: pip install 'action-platform[mcp]'"
        ) from e

    argv = ["--http", "--host", host, "--port", str(port)] if http else []

    if remote:
        argv.append("--remote")

    main(argv)
