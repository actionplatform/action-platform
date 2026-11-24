"""`action-platform-api users`."""

from __future__ import annotations

import secrets
from urllib.parse import urlencode

import typer

from app.cli.context import auth_service, public_url, read_secret
from app.services.auth.recovery import LINK_TTL

app = typer.Typer(
    help="Accounts on this instance: list, create, reset a password, disable, enable.",
    no_args_is_help=True,
)

SIGNED_OUT = "the CLI and MCP signed in as this user have to log in again"


def _link(token: str) -> str:
    return f"{public_url()}/reset-password?{urlencode({'token': token})}"


def _hours() -> int:
    return int(LINK_TTL.total_seconds() // 3600)


@app.command("list")
def list_users() -> None:
    """Every account: email, name, status and the organizations it belongs to."""
    with auth_service() as auth:
        rows = auth.users()

    if not rows:
        typer.echo("no users yet")
        return

    for user, memberships in rows:
        status = "disabled" if user.disabled_at else "active"
        organizations = ", ".join(f"{o.slug}:{role}" for o, role in memberships) or "-"
        typer.echo(
            f"{user.email}\t{user.name}\t{status}\t{user.created_at:%Y-%m-%d}\t{organizations}"
        )


@app.command("create")
def create(
    email: str = typer.Argument(..., help="The new account's email"),
    name: str = typer.Option(..., "--name", help="Display name"),
    organization: str = typer.Option(
        "", "--org", help="Add the account to this organization (slug or id)"
    ),
    role: str = typer.Option(
        "developer",
        "--role",
        help="Role in --org: owner, admin, deployer, developer, viewer",
    ),
    password_stdin: bool = typer.Option(
        False,
        "--password-stdin",
        help="Read the password from stdin instead of printing a set-password link",
    ),
) -> None:
    """Create an account; prints a one-time link to choose its password unless --password-stdin is given."""
    password = read_secret("Password") if password_stdin else None

    if password is None:
        public_url()

    with auth_service() as auth:
        org = auth.organization_by_slug(organization) if organization else None
        user = auth.create_user(name, email, password, org, role)
        token = None if password else auth.reset_token(user, LINK_TTL)

    typer.echo(f"created {user.email}" + (f" in {org.slug} as {role}" if org else ""))

    if token:
        typer.echo(f"set-password link, single use, valid {_hours()} hours:")
        typer.echo(_link(token))


@app.command("reset-password")
def reset_password(
    email: str = typer.Argument(..., help="The account's email"),
    password_stdin: bool = typer.Option(
        False,
        "--password-stdin",
        help="Read the new password from stdin instead of printing a reset link",
    ),
) -> None:
    """Replace the password, end every session and revoke every API token; prints a one-time reset link unless --password-stdin is given."""
    password = read_secret("New password") if password_stdin else None

    if password is None:
        public_url()

    with auth_service() as auth:
        user = auth.user_by_email(email)
        sessions, tokens = auth.set_password(
            user, password or secrets.token_urlsafe(32)
        )
        token = None if password else auth.reset_token(user, LINK_TTL)

    typer.echo(
        f"password of {user.email} replaced: {sessions} session(s) ended, "
        f"{tokens} API token(s) revoked; {SIGNED_OUT}"
    )

    if token:
        typer.echo(
            f"the old password no longer works; reset link, single use, valid {_hours()} hours:"
        )
        typer.echo(_link(token))


@app.command("disable")
def disable(
    email: str = typer.Argument(..., help="The account's email"),
) -> None:
    """Block sign-in, end every session and refuse the account's API tokens until it is enabled again."""
    with auth_service() as auth:
        user = auth.user_by_email(email)
        sessions = auth.disable_user(user)

    typer.echo(
        f"disabled {user.email}: {sessions} session(s) ended and its API tokens refused; "
        "the CLI and MCP signed in as this user stop working"
    )


@app.command("enable")
def enable(
    email: str = typer.Argument(..., help="The account's email"),
) -> None:
    """Allow a disabled account to sign in again; its unexpired API tokens answer again."""
    with auth_service() as auth:
        user = auth.user_by_email(email)
        auth.enable_user(user)

    typer.echo(f"enabled {user.email}")
