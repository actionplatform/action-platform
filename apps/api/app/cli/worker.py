"""`action-platform-api worker`."""

from __future__ import annotations

import typer

from action_platform.core.exception import ActionPlatformError
from action_platform.settings import settings
from app.core.auth.secrets import Secrets
from app.core.db import Database
from app.services.jobs.worker import Worker
from app.services.jobs.workers import Workers


def run(
    once: bool = typer.Option(False, "--once", help="Drain the queue and exit"),
    interval: float = typer.Option(
        2.0, "--interval", help="Seconds between polls when idle"
    ),
    name: str = typer.Option(
        "", "--name", help="How this worker signs the jobs it takes"
    ),
    concurrency: int = typer.Option(
        1, "--concurrency", min=1, max=32, help="Jobs run at the same time"
    ),
    kinds: str = typer.Option(
        "",
        "--kinds",
        help="Only these job kinds, comma-separated (e.g. deploy,destroy); default every kind",
    ),
    check: bool = typer.Option(
        False,
        "--check",
        help="Exit 0 when the worker called --name wrote a heartbeat in the last minute, 1 otherwise; runs nothing",
    ),
) -> None:
    """Run queued jobs — sync, release, deploy, push, imports — against the API's database and workspaces."""

    if not settings.database.url:
        raise ActionPlatformError("no database: set AP_DATABASE_URL")

    database = Database(settings.database.url, settings.database.pool_size)

    if check:
        raise typer.Exit(_check(database, name))

    if settings.database.auto_migrate:
        database.migrate()
    elif database.behind():
        raise ActionPlatformError(
            "database behind head: run `action-platform-api db migrate` before the worker"
        )
    worker = Worker(
        database,
        Secrets(settings.api.auth_secret) if settings.api.auth_secret else None,
        name or None,
    )
    only = [k.strip() for k in kinds.split(",") if k.strip()] or None
    typer.echo(
        f"worker {worker.name} on {database.dialect}"
        + (f" · {concurrency} at a time" if concurrency > 1 else "")
        + (f" · {', '.join(only)}" if only else "")
    )
    done = worker.run(interval=interval, once=once, concurrency=concurrency, kinds=only)

    if once:
        typer.echo(f"{done} job(s) done")


def _check(database: Database, name: str) -> int:
    if not name:
        typer.echo("--check needs --name: the worker to look for", err=True)

        return 2

    try:
        row = Workers(database).get(name)
    except Exception as e:
        typer.echo(f"cannot read the worker table: {e}", err=True)

        return 1

    if row is None:
        typer.echo(f"worker {name} has not started", err=True)

        return 1

    if not Workers.alive(row):
        typer.echo(
            f"worker {name} was last seen at {row.last_seen:%H:%M:%S} UTC", err=True
        )

        return 1

    typer.echo(f"worker {name} alive")

    return 0
