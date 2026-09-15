"""`action-platform-api worker`."""

from __future__ import annotations

import typer

from action_platform.core.exception import ActionPlatformError
from action_platform.settings import settings
from app.core.auth.secrets import Secrets
from app.core.db import Database
from app.services.jobs.worker import Worker


def run(
    once: bool = typer.Option(False, "--once", help="Drain the queue and exit"),
    interval: float = typer.Option(
        2.0, "--interval", help="Seconds between polls when idle"
    ),
    name: str = typer.Option(
        "", "--name", help="How this worker signs the jobs it takes"
    ),
) -> None:
    """Run queued jobs — sync, release, deploy, push, imports — against the API's database and workspaces."""

    if not settings.DATABASE_URL:
        raise ActionPlatformError("no database: set AP_DATABASE_URL")

    database = Database(settings.DATABASE_URL, settings.DATABASE_POOL_SIZE)

    if settings.DATABASE_AUTO_MIGRATE:
        database.migrate()
    elif database.behind():
        raise ActionPlatformError(
            "database behind head: run `action-platform-api db migrate` before the worker"
        )
    worker = Worker(
        database,
        Secrets(settings.AUTH_SECRET) if settings.AUTH_SECRET else None,
        name or None,
    )
    typer.echo(f"worker {worker.name} on {database.dialect}")
    done = worker.run(interval=interval, once=once)

    if once:
        typer.echo(f"{done} job(s) done")
