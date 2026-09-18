"""`action-platform-api serve`."""

from __future__ import annotations

import typer

from action_platform.settings import settings
from app.api import app as server


def run(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(7788, "--port"),
    cors: str = typer.Option(
        "http://localhost:3000",
        "--cors",
        help="Comma-separated origins allowed to call the API from a browser",
    ),
    reload: bool = typer.Option(
        False, "--reload", help="Restart on code changes (development)"
    ),
    workers: int = typer.Option(
        1, "--workers", min=1, max=64, help="Uvicorn worker processes (AP_API_WORKERS)"
    ),
) -> None:
    """Serve the JSON API the web app talks to: apps registry, git-flow, releases, deploys."""
    origins = [o.strip() for o in cors.split(",") if o.strip()]
    count = workers if workers > 1 else int(settings.env("AP_API_WORKERS") or 1)
    typer.echo(
        f"action-platform api on http://{host}:{port}"
        + (f" · {count} workers" if count > 1 else "")
    )
    server.serve(host, port, origins, reload=reload, workers=count)
