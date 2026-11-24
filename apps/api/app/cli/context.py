"""The auth service on the API's database, for the operator commands run inside the API container."""

from __future__ import annotations

import getpass
import sys
from contextlib import contextmanager
from typing import Iterator

from action_platform.core.exception import ActionPlatformError
from action_platform.settings import settings
from app.core.auth.secrets import Secrets
from app.core.db import Database
from app.services.auth.service import AuthService


@contextmanager
def auth_service() -> Iterator[AuthService]:
    if not settings.database.url:
        raise ActionPlatformError("no database: set AP_DATABASE_URL")

    if not settings.api.auth_secret:
        raise ActionPlatformError("no auth secret: set AP_AUTH_SECRET")

    database = Database(settings.database.url, settings.database.pool_size)

    try:
        if database.behind():
            raise ActionPlatformError(
                "database behind head: run `action-platform-api db migrate` first"
            )

        with database.session() as db:
            yield AuthService(db, Secrets(settings.api.auth_secret))
    finally:
        database.dispose()


def read_secret(label: str) -> str:
    """One line from stdin, never echoed: piped in, or typed at a hidden prompt."""
    value = (
        getpass.getpass(f"{label}: ") if sys.stdin.isatty() else sys.stdin.readline()
    )
    value = value.rstrip("\r\n")

    if not value:
        raise ActionPlatformError(f"no {label.lower()} on stdin")

    return value


def public_url() -> str:
    url = settings.api.public_url.rstrip("/")

    if not url:
        raise ActionPlatformError(
            "AP_PUBLIC_URL is empty: set it to the web app's address to print a link"
        )

    return url
