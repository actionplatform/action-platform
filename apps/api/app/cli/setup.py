"""`action-platform-api setup`."""

from __future__ import annotations

import typer

from action_platform.core.exception import ActionPlatformError
from app.cli.context import auth_service

app = typer.Typer(
    help="First-run setup: the token the first account needs.",
    no_args_is_help=True,
)


@app.command("token")
def token() -> None:
    """Print the setup token the first sign-up asks for; refuses once an account exists."""
    with auth_service() as auth:
        if auth.user_count() > 0:
            raise ActionPlatformError(
                "setup is closed: an account already exists; sign in, or reset a password with `action-platform-api users reset-password`"
            )

        value = auth.setup_token()

    typer.echo(value)
