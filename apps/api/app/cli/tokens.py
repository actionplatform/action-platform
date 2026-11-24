"""`action-platform-api tokens`."""

from __future__ import annotations

from datetime import timedelta

import typer

from action_platform.core.access import Grant, parse_scopes
from action_platform.core.exception import ActionPlatformError
from app.cli.context import auth_service

app = typer.Typer(
    help="API tokens for automation, issued without a browser.",
    no_args_is_help=True,
)


@app.command("issue")
def issue(
    email: str = typer.Argument(..., help="The account the token acts as"),
    scope: str = typer.Option(
        "read",
        "--scope",
        help="read, write, release, admin (comma-separated); narrowed to the account's role",
    ),
    organization: str = typer.Option(
        "*", "--org", help="One organization (slug or id), or * for all of them"
    ),
    project: str = typer.Option("", "--project", help="Only this project (id)"),
    app_id: str = typer.Option("", "--app", help="Only this app of --project (id)"),
    name: str = typer.Option("automation", "--name", help="Label shown in the web app"),
    days: int = typer.Option(
        0,
        "--days",
        min=0,
        help="Lifetime in days, at most the default (90, or 30 with admin)",
    ),
) -> None:
    """Print a bearer token for the account on stdout; what it carries goes to stderr."""
    scopes = parse_scopes(scope)

    if not scopes:
        raise ActionPlatformError(
            "--scope needs at least one of read, write, release, admin"
        )

    if app_id and not project:
        raise ActionPlatformError("--app needs --project")

    with auth_service() as auth:
        user = auth.user_by_email(email)
        org = None if organization == "*" else auth.organization_by_slug(organization)
        token, raw = auth.issue_token_for(
            user.id,
            Grant(scopes, org.id if org else "*", project or None, app_id or None),
            name,
            timedelta(days=days) if days else None,
        )
        granted = token.scope
        expires = token.expires_at

    typer.echo(
        f"token for {user.email}: {granted} on {org.slug if org else 'all organizations'}"
        + (f" / project {project}" if project else "")
        + (f" / app {app_id}" if app_id else "")
        + f", expires {expires:%Y-%m-%d}",
        err=True,
    )
    typer.echo(raw)
