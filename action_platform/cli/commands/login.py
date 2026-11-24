"""`action-platform login` / `logout` / `whoami`."""

from __future__ import annotations

import getpass
import os
import sys
from typing import Any

import typer

from action_platform.core.exception import ActionPlatformError
from action_platform.remote import credentials
from action_platform.remote.client import (
    DEFAULT_SCOPE,
    Remote,
    login as device_login,
    login_with_token,
)
from action_platform.remote.schemas import Me


def login(
    server: str = typer.Argument(
        ..., help="URL of the hosted platform, e.g. https://platform.example.com"
    ),
    no_browser: bool = typer.Option(
        False, "--no-browser", help="Print the URL instead of opening it"
    ),
    scope: str = typer.Option(
        DEFAULT_SCOPE,
        "--scope",
        help="What the token may do, within your role: read, write, release, admin (comma-separated). Everything by default; narrowed to your role, and adjustable in the browser when approving.",
    ),
    name: str | None = typer.Option(
        None, "--name", help="Label for the token in Settings (default user@host)"
    ),
    token: bool = typer.Option(
        False,
        "--token",
        help="No browser: keep a token created in the web app or by `action-platform-api tokens issue`, read from AP_TOKEN or stdin",
    ),
) -> None:
    """Sign in to a hosted Action Platform through the browser, or with --token; a scoped bearer token is kept in ~/.action-platform."""
    if token:
        creds, who = login_with_token(server, _read_token())
        typer.echo(f"logged in to {creds.server} — {_describe(creds, who)}")
        return

    creds = device_login(
        server, open_browser=not no_browser, echo=typer.echo, scope=scope, name=name
    )
    typer.echo(
        f"logged in to {creds.server} — {_describe(creds, Remote(creds.server, creds.token).whoami())}"
    )


def _read_token() -> str:
    value = os.environ.get("AP_TOKEN") or (
        getpass.getpass("Token: ") if sys.stdin.isatty() else sys.stdin.readline()
    )
    value = value.strip()

    if not value:
        raise ActionPlatformError("no token: pipe it on stdin or set AP_TOKEN")

    return value


def logout() -> None:
    """Forget the saved token."""
    typer.echo("logged out" if credentials.clear() else "not logged in")


def whoami() -> None:
    """Show which platform and account the CLI is using."""
    creds = credentials.load()

    if creds is None:
        raise ActionPlatformError("not logged in: run `action-platform login <server>`")

    typer.echo(
        f"{creds.server} — {_describe(creds, Remote(creds.server, creds.token).whoami())}"
    )


def _name(part: dict[str, Any]) -> str:
    return str(part.get("name") or part.get("id") or "?")


def _describe(creds: credentials.Credentials, who: Me) -> str:
    email = who.user.get("email", "?")
    scope = " ".join(who.scope or []) or creds.scope or "session"
    reach = " / ".join(
        _name(part) for part in (who.organization, who.project, who.app) if part
    )

    return f"{email} — scope: {scope}" + (f" — on {reach}" if reach else "")
