"""`action-platform init` command."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from action_platform.core.wiring import wired
from action_platform.core.exception import TemplateError
from action_platform.core.scaffold.catalog import Matrix, load_matrix
from action_platform.core.scaffold import identity
from action_platform.logging import logger

CI_PROVIDERS = ["github", "gitlab", "jenkins", "bitbucket"]

console = Console()


def run(
    type_: str | None = typer.Argument(
        None, metavar="TYPE", help="web, library, mcp, ..."
    ),
    stack: str | None = typer.Argument(None, help="python, go, node, ..."),
    template: str | None = typer.Argument(
        None, help="fastapi, gin, ... (default per stack)"
    ),
    name: str | None = typer.Option(None, "--name", "-n", help="Project name"),
    ci: str | None = typer.Option(
        None, "--ci", help="CI provider: " + ", ".join(CI_PROVIDERS)
    ),
    cloud: str | None = typer.Option(
        None, "--cloud", help="Deploy overlay: aws/lambda, docker, ..."
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Where to create the project"
    ),
    owner: str | None = typer.Option(
        None,
        "--owner",
        help="Account or organization that owns the repository (default: the account the host's credentials belong to, else asked)",
    ),
    author: str | None = typer.Option(
        None,
        "--author",
        help="Author in the manifest and the LICENSE (default: git config user.name)",
    ),
    license_: str | None = typer.Option(
        None,
        "--license",
        help="mit, apache-2.0 or none (default: asked; none without a terminal)",
    ),
    host: str | None = typer.Option(
        None,
        "--host",
        help="github, gitlab or bitbucket (default: gitlab or bitbucket when --ci names it, else github)",
    ),
    push: bool = typer.Option(
        True,
        "--push/--no-push",
        help="Create the remote repo via [source_host] and push (default: on)",
    ),
    public: bool = typer.Option(
        False,
        "--public/--private",
        help="With --push: a public repository (default: private)",
    ),
    list_: bool = typer.Option(False, "--list", "-l", help="Show the template matrix"),
    update: bool = typer.Option(False, "--update", help="Refresh the templates cache"),
    source: str | None = typer.Option(
        None,
        "--source",
        help="Another templates repository, url[@ref]; default is the official one",
    ),
) -> None:
    """Bootstrap a project from the templates matrix."""
    repo, matrix = load_matrix(update=update, source=source)

    if list_:
        print_matrix(matrix)
        return

    if type_ is None:
        type_ = choose("type", matrix.types())
    if stack is None and matrix.stacks(type_):
        stack = choose("stack", matrix.stacks(type_))
    if template is None and stack is not None:
        leaves = matrix.templates(type_, stack)
        if len(leaves) > 1:
            template = choose("template", [leaf.template for leaf in leaves])

    leaf = matrix.resolve(type_, stack, template)

    if name is None:
        name = typer.prompt("project name")
    if ci is None and leaf.type != "empty":
        ci = choose("ci", CI_PROVIDERS)
    if ci is not None and ci not in CI_PROVIDERS:
        raise TemplateError(f"unknown ci: {ci} (available: {', '.join(CI_PROVIDERS)})")

    host = host or identity.host_for(ci)
    interactive = sys.stdin.isatty()

    if license_ is None:
        license_ = choose("license", list(identity.LICENSES)) if interactive else "none"

    identity.check(license_, host)
    owner = owner or identity.account(host)

    if not owner and push:
        if not interactive:
            raise TemplateError(
                f"no owner for the {host} repository: pass --owner, or --no-push"
            )

        owner = typer.prompt(f"{host} account or organization that owns the repository")

    extra = {
        "author": identity.git_author() if author is None else author,
        "license": license_,
        "source_host": host,
    }

    if owner:
        extra["github_owner"] = owner

    project = wired.scaffolder().generate(
        repo, leaf, name=name, ci=ci, output=output or Path.cwd(), extra=extra
    )
    logger.info("created %s", project)

    if cloud is not None:
        wired.scaffolder().apply_cloud(repo, matrix.cloud(cloud), project)
        logger.info("applied cloud %s", cloud)

    if push:
        url = wired.scaffolder().push(project, private=not public)
        logger.info("pushed to %s", url)


def choose(label: str, options: list[str]) -> str:
    console.print(f"[bold]{label}[/bold]")
    for i, opt in enumerate(options, 1):
        console.print(f"  {i}. {opt}")
    while True:
        raw = typer.prompt(f"{label} [1-{len(options)}]")
        if raw in options:
            return raw
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        console.print("[red]invalid choice[/red]")


def print_matrix(matrix: Matrix) -> None:
    table = Table(title="Projects")
    table.add_column("type")
    table.add_column("stack")
    table.add_column("template")
    table.add_column("description")
    for leaf in matrix.leaves:
        tpl = f"{leaf.template} *" if leaf.default else leaf.template
        table.add_row(leaf.type, leaf.stack, tpl, leaf.description)
    console.print(table)
    console.print("[dim]* default template for the stack[/dim]\n")

    clouds = Table(title="Clouds")
    clouds.add_column("cloud")
    clouds.add_column("types")
    clouds.add_column("languages")
    clouds.add_column("description")
    for cloud in matrix.clouds:
        clouds.add_row(
            cloud.name,
            ", ".join(cloud.types) or "any",
            ", ".join(cloud.languages) or "any",
            cloud.description,
        )
    console.print(clouds)

    services = Table(title="Services")
    services.add_column("service")
    services.add_column("providers")
    services.add_column("description")

    for service in matrix.services:
        services.add_row(
            service.name, ", ".join(service.providers), service.description
        )

    console.print(services)
