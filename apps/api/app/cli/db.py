"""`action-platform-api db`."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import typer

from action_platform.core.exception import ActionPlatformError
from action_platform.settings import settings
from app.core.db import Database
from app.core.db.dump import Postgres

app = typer.Typer(
    help="Database the API owns: migrations, status, backup and restore.",
    no_args_is_help=True,
)


def _url(url: str | None) -> str:
    chosen = url or settings.database.url

    if not chosen:
        raise ActionPlatformError("no database: set AP_DATABASE_URL or pass --url")

    return chosen


def _database(url: str | None):
    return Database(_url(url), settings.database.pool_size)


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


@app.command("backup")
def backup(
    out: str = typer.Option(
        "",
        "--out",
        help="File to write, - for stdout; default action_platform-<UTC time>.sql here",
    ),
    url: str = typer.Option("", "--url", help="Overrides AP_DATABASE_URL"),
) -> None:
    """Dump the database as plain SQL with pg_dump."""
    postgres = Postgres.from_url(_url(url))

    if out == "-":
        postgres.backup(None)
        return

    path = Path(
        out or f"action_platform-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.sql"
    )
    postgres.backup(path)
    typer.echo(f"wrote {path}")


@app.command("restore")
def restore(
    file: str = typer.Argument(..., help="A plain SQL dump, - for stdin"),
    force: bool = typer.Option(
        False, "--force", help="Drop every table first when the database has some"
    ),
    url: str = typer.Option("", "--url", help="Overrides AP_DATABASE_URL"),
) -> None:
    """Load a dump with psql in one transaction; run `db migrate` afterwards."""
    postgres = Postgres.from_url(_url(url))

    if file != "-" and not Path(file).is_file():
        raise ActionPlatformError(f"no dump at {file}")

    dump = sys.stdin.buffer.read() if file == "-" else Path(file).read_bytes()
    postgres.restore(dump, force=force)
    typer.echo("restored; run action-platform-api db migrate next", err=True)
