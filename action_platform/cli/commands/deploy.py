"""`action-platform deploy | rollback | diagnose | destroy` commands."""

from __future__ import annotations

import time
from pathlib import Path

import typer
from rich.console import Console

from action_platform.bootstrap import project as open_project
from action_platform.core.facade import ActionPlatform
from action_platform.core.config import Config
from action_platform.core.exception import ActionPlatformError, DeployError
from action_platform.remote.client import Remote
from action_platform.remote.schemas import AppRef, ProjectRow
from action_platform.logging import logger
from action_platform.core.files import CONFIG_FILE

console = Console()

TARGET = typer.Option(
    None, "--target", help="Filter by target name (aws/lambda, docker, ...)"
)
STAGE = typer.Option(
    None,
    "--stage",
    "--scope",
    help="The scope to deploy to (default: prod on main/master, else dev)",
)


def _tool() -> ActionPlatform:
    return open_project()


def run(
    target: str | None = TARGET,
    stage: str | None = STAGE,
    dry_run: bool = typer.Option(False, "--dry-run"),
    version: str | None = typer.Option(
        None,
        "--version",
        help="Release to ship (tag v<version>); default: the tag HEAD sits on",
    ),
) -> None:
    """Ship a release to the [deploy] target in platform.toml — a tag, never a working tree."""
    for r in _tool().deploy(
        target=target, dry_run=dry_run, stage=stage, version=version
    ):
        logger.info(
            "deploy %s ok=%s version=%s url=%s", r.target, r.ok, r.version, r.url
        )

        if not r.ok:
            raise DeployError(r.error or f"{r.target} failed")


def rollback(
    to_version: str | None = typer.Argument(
        None, help="Version to return to (default: previous)"
    ),
    target: str | None = TARGET,
    stage: str | None = STAGE,
) -> None:
    """Return the target to a previous version."""
    try:
        _tool().rollback(target=target, to_version=to_version, stage=stage)
    except NotImplementedError as e:
        raise DeployError(str(e)) from e
    logger.info("rollback done")


def diagnose(target: str | None = TARGET, stage: str | None = STAGE) -> None:
    """Health, status and URL of the deployed target."""
    try:
        results = _tool().diagnose(target=target, stage=stage)
    except NotImplementedError as e:
        raise DeployError(str(e)) from e
    for d in results:
        mark = "[green]ok[/green]" if d.ok else "[red]not ok[/red]"
        console.print(f"[bold]{d.target}[/bold] {mark} {d.status}")

        if d.url:
            console.print(f"  url: {d.url}")

        for k, v in d.details.items():
            console.print(f"  {k}: {v}")


def scopes() -> None:
    """Where this repository's releases are deployed: `[[scopes]]`, or the `[deploy]` targets read as scopes."""
    config = Config.from_toml(Path.cwd() / CONFIG_FILE)

    for scope in config.scopes:
        console.print(
            f"[bold]{scope.name}[/bold] {scope.kind} [dim]{scope.criticality}[/dim]"
        )


def readiness(
    target: str | None = TARGET,
    stage: str | None = STAGE,
    version: str | None = typer.Option(
        None,
        "--version",
        help="Release to check (tag v<version>); default: the tag HEAD sits on",
    ),
) -> None:
    """Whether a release can reach a stage: configuration, manifests, credentials, permissions, the destination's state. Nothing is built or changed."""
    tool = _tool()
    chosen = stage or tool.releaser.context().stage
    checks = tool.check_readiness(chosen, version=version, target=target)

    for c in checks:
        mark = (
            "[green]ok[/green]"
            if c.ok
            else "[yellow]warn[/yellow]"
            if c.severity == "warning"
            else "[red]fail[/red]"
        )
        where = f" [dim]{c.target}[/dim]" if c.target else ""
        console.print(f"{mark} [bold]{c.id}[/bold]{where} {c.detail}")

        if c.fix and not c.ok:
            console.print(f"     fix: {c.fix}")

    blocking = [c for c in checks if c.blocking]
    console.print(
        f"[bold]{chosen}[/bold]: "
        + (
            "[green]deployable[/green]"
            if not blocking
            else f"[red]not deployable[/red] ({len(blocking)} blocking)"
        )
    )

    if blocking:
        raise typer.Exit(1)


def destroy(
    target: str | None = TARGET,
    stage: str | None = STAGE,
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Tear the target down. Irreversible."""
    if not yes and not typer.confirm("Delete the deployed target?"):
        raise typer.Abort()

    try:
        _tool().destroy(target=target, stage=stage)
    except NotImplementedError as e:
        raise DeployError(str(e)) from e
    logger.info("destroy done")


def _remote_app(app: str | None) -> tuple[Remote, ProjectRow, AppRef]:
    remote = Remote.from_credentials()
    wanted = app or Config.from_toml(Path.cwd() / CONFIG_FILE).project_name

    for project in remote.projects():
        for row in project.apps:
            if wanted in (row.registry_id, row.id, row.name):
                return remote, project, row

    raise ActionPlatformError(
        f"no app {wanted!r} on the platform: `action-platform login` and check the name"
    )


def deployments(
    app: str | None = typer.Option(
        None,
        "--app",
        help="App id or name on the platform; default: this repository's project name",
    ),
    sync: bool = typer.Option(
        False,
        "--sync",
        help="Ask the observed pipelines for new runs and verify versions first",
    ),
) -> None:
    """What arrived at each of the app's targets on the platform, whoever shipped it."""
    remote, project, row = _remote_app(app)
    body = (
        remote.sync_deployments(project.id, row.id)
        if sync
        else remote.deployments(project.id, row.id)
    )

    for target in body.targets:
        source = target.workflow or target.job or ""
        console.print(
            f"[bold]{target.name}[/bold] {target.kind} · {target.run_by}{' · ' + source if source else ''}"
        )

        for d in [d for d in body.deployments if d.target == target.name][:10]:
            stage = f" {d.stage}" if d.stage else ""
            console.print(
                f"  {d.version}{stage}  {d.status}  {d.executor}  {d.finished_at or d.started_at or ''}"
            )

    if body.error:
        console.print(f"[yellow]{body.error}[/yellow]")


def logs(
    job: str = typer.Argument(..., help="The job id the platform answered with"),
    follow: bool = typer.Option(
        False, "--follow", "-f", help="Keep printing until the job finishes"
    ),
) -> None:
    """What the worker wrote while running a job — a deploy, a release, a readiness check — on the hosted platform."""
    remote = Remote.from_credentials()
    after = 0

    while True:
        page = remote.job_logs(job, after=after)

        for row in page.lines:
            console.print(row.line, highlight=False, markup=False)

        after = page.next

        if page.finished or not follow:
            if follow or page.finished:
                console.print(f"[dim]job {page.status}[/dim]")

            return

        time.sleep(1.5)


def record(
    target: str = typer.Argument(
        ..., help="A target name of [deploy] in platform.toml"
    ),
    version: str = typer.Argument(..., help="The release shipped: 1.4.0 or v1.4.0"),
    stage: str | None = STAGE,
    url: str | None = typer.Option(None, "--url", help="Where it can be seen"),
    failed: bool = typer.Option(False, "--failed", help="Record a failed delivery"),
    app: str | None = typer.Option(
        None,
        "--app",
        help="App id or name on the platform; default: this repository's project name",
    ),
) -> None:
    """Record on the platform a deployment made outside it. A deployment always references a release."""
    remote, project, row = _remote_app(app)
    d = remote.record_deployment(
        project.id, row.id, target, version, stage, url, None, not failed
    )
    console.print(f"recorded {d.target} {d.version} {d.status}")
