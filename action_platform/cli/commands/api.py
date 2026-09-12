"""`action-platform api` command."""

from __future__ import annotations

from pathlib import Path

import typer

from action_platform.core.exception import ActionPlatformError


def run(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(7788, "--port"),
    cors: str = typer.Option(
        "http://localhost:3000",
        "--cors",
        help="Comma-separated origins allowed to call the API from a browser",
    ),
    register: bool = typer.Option(
        True,
        "--register/--no-register",
        help="Register the current directory when it holds a platform.toml",
    ),
) -> None:
    """Serve the JSON API the web app talks to: projects registry, git-flow, releases, deploys."""
    try:
        from action_platform.api import server
        from action_platform.api.registry import Registry
    except ModuleNotFoundError as e:
        raise ActionPlatformError(
            "API support is not installed: pip install 'action-platform[api]'"
        ) from e

    if register and (Path.cwd() / "platform.toml").exists():
        entry = Registry().add(Path.cwd())
        typer.echo(f"registered {entry.name} ({entry.id})")

    origins = [o.strip() for o in cors.split(",") if o.strip()]
    typer.echo(f"action-platform api on http://{host}:{port}")
    server.serve(host, port, origins)
