"""`action-platform access …` — access on the organization's services (GitHub, built in, and those the platform's plugins own), through the platform the CLI is logged in to; JSON on stdout."""

from __future__ import annotations

import json
from typing import Any, Optional

import typer

from action_platform.remote.client import Remote

app = typer.Typer(
    help="Who has access to what on the organization's services, and keep it that way.",
    no_args_is_help=True,
)

Organization = typer.Option(
    None,
    "--organization",
    help="Organization id or slug, for a token that spans every one",
)
Apply = typer.Option(False, help="Change the services; without it, show the plan")


def _print(model: Any) -> None:
    typer.echo(json.dumps(model.model_dump(exclude_none=True), indent=2))


@app.command("audit")
def audit(
    service: Optional[str] = typer.Option(None, help="Only this service"),
    organization: Optional[str] = Organization,
) -> None:
    """Drift per service against the organization."""
    _print(Remote.from_credentials().access_audit(service, organization))


@app.command("who")
def who(
    person: Optional[str] = typer.Option(None, help="A member's email"),
    service: Optional[str] = typer.Option(None, help="A service name"),
    organization: Optional[str] = Organization,
) -> None:
    """A person's accounts and access, or every account on a service."""
    _print(Remote.from_credentials().access_who(person, service, organization))


@app.command("grant")
def grant(
    person: str,
    service: str,
    resource: str,
    level: str,
    account: Optional[str] = typer.Option(
        None, help="The person's account on the service"
    ),
    apply: bool = Apply,
    organization: Optional[str] = Organization,
) -> None:
    """Give one person access on one service."""
    _print(
        Remote.from_credentials().access_grant(
            person, service, resource, level, account, apply, organization
        )
    )


@app.command("revoke")
def revoke(
    person: str,
    service: str,
    resource: str,
    apply: bool = Apply,
    organization: Optional[str] = Organization,
) -> None:
    """Take one grant away from one person."""
    _print(
        Remote.from_credentials().access_revoke(
            person, service, resource, apply, organization
        )
    )


@app.command("offboard")
def offboard(
    person: str,
    apply: bool = Apply,
    remove_from_platform: bool = typer.Option(
        False, help="Also remove the platform membership"
    ),
    organization: Optional[str] = Organization,
) -> None:
    """Remove a person from every service."""
    _print(
        Remote.from_credentials().access_offboard(
            person, apply, remove_from_platform, organization
        )
    )


@app.command("sync")
def sync(
    service: Optional[str] = typer.Option(None, help="Only this service"),
    apply: bool = Apply,
    reimport: bool = typer.Option(
        False, help="Import live state into the mapping again"
    ),
    link: list[str] = typer.Option(
        [], help="email:service:account, for an import; repeatable"
    ),
    organization: Optional[str] = Organization,
) -> None:
    """Make every service match the mapping; a service not imported yet is only imported."""
    links: dict[str, dict[str, str]] = {}

    for row in link:
        email, name, account = row.split(":", 2)
        links.setdefault(email, {})[name] = account

    _print(
        Remote.from_credentials().access_sync(
            service, apply, reimport, links or None, organization
        )
    )
