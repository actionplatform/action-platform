"""`action-platform-api`: serve the API, run a worker, manage the database, its users and tokens."""

from app.cli.app import app, main

__all__ = ["app", "main"]
