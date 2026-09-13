"""`action-platform login` / `logout` / `whoami`."""

from __future__ import annotations

import typer

from action_platform.core.exception import ActionPlatformError
from action_platform.remote import credentials
from action_platform.remote.client import DEFAULT_SCOPE, Remote, login as device_login


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
        help="What the token may do, within your role: read, write, release, admin (comma-separated). Adjustable in the browser when approving.",
    ),
    name: str | None = typer.Option(
        None, "--name", help="Label for the token in Settings (default user@host)"
    ),
) -> None:
    """Sign in to a hosted Action Platform through the browser; a scoped bearer token is kept in ~/.action-platform."""
    creds = device_login(
        server, open_browser=not no_browser, echo=typer.echo, scope=scope, name=name
    )
    who = Remote(creds.server, creds.token).whoami()
    email = who.get("user", {}).get("email", "?")
    org = (who.get("organization") or {}).get("name")
    typer.echo(
        f"logged in to {creds.server} as {email}"
        + (f" ({org})" if org else "")
        + f" — scope: {creds.scope or 'session'}"
    )


def logout() -> None:
    """Forget the saved token."""
    typer.echo("logged out" if credentials.clear() else "not logged in")


def whoami() -> None:
    """Show which platform and account the CLI is using."""
    creds = credentials.load()

    if creds is None:
        raise ActionPlatformError("not logged in: run `action-platform login <server>`")

    who = Remote(creds.server, creds.token).whoami()
    email = who.get("user", {}).get("email", "?")
    scope = " ".join(who.get("scope") or []) or creds.scope or "session"
    typer.echo(f"{creds.server} — {email} — scope: {scope}")
