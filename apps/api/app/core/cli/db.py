"""`action-platform-api db`."""

from __future__ import annotations

import typer

from action_platform.core.exception import ActionPlatformError
from action_platform.settings import settings
from app.core.db import Database

app = typer.Typer(
    help="Database the API owns: migrations and status.", no_args_is_help=True
)


def _database(url: str | None):
    chosen = url or settings.DATABASE_URL

    if not chosen:
        raise ActionPlatformError("no database: set AP_DATABASE_URL or pass --url")

    return Database(chosen, settings.DATABASE_POOL_SIZE)


@app.command("migrate")
def migrate(
    url: str = typer.Option("", "--url", help="Overrides AP_DATABASE_URL"),
) -> None:
    """Bring the schema to the latest revision; a database created by the web app is adopted as is."""
    database = _database(url)
    adopted = database.adopted_from_web()
    revision = database.migrate()
    typer.echo(f"{'adopted web schema, ' if adopted else ''}at revision {revision}")


@app.command("status")
def status(
    url: str = typer.Option("", "--url", help="Overrides AP_DATABASE_URL"),
) -> None:
    """Show the current and the latest revision."""
    database = _database(url)
    current = database.current_revision()
    head = database.head_revision()
    state = "up to date" if current == head else "behind" if current else "empty"
    typer.echo(f"{database.dialect}: current={current or '-'} head={head} ({state})")
