"""`action-platform plugin` — what is installed, what an index offers, switch on and off, install and remove."""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.table import Table

from action_platform.plugins import PluginError, PluginState, registry
from action_platform.plugins.installer import IndexEntry, PipInstaller, lookup

app = typer.Typer(
    help="Plugins installed next to the CLI: tools, overlays, deploy targets.",
    no_args_is_help=True,
)
console = Console()


@app.command("list")
def list_() -> None:
    """Installed plugins, enabled or not, and what they bring."""
    rows = registry.installed().rows()

    if not rows:
        console.print("no plugins installed — action-platform plugin search <name>")

        return

    table = Table(box=None, pad_edge=False)

    for column in ("slug", "version", "enabled", "package", "description"):
        table.add_column(column)

    for row in rows:
        table.add_row(
            row["slug"],
            row["version"],
            "yes" if row["enabled"] else "no",
            row["package"],
            row["description"],
        )

    console.print(table)


@app.command("search")
def search(
    slug: str = typer.Argument(..., help="Plugin slug, e.g. aws-lambda"),
) -> None:
    """What the indexes know about a plugin."""
    state = PluginState.load()
    index, row = lookup(state, slug)

    console.print(f"[bold]{row.slug}[/bold] — {row.description}")
    console.print(f"  package   {row.pypi}  latest {row.latest or '?'}")
    console.print(f"  repo      {row.repo}")
    console.print(f"  verified  {'yes' if row.verified else 'no'}   index {index}")

    if row.min_core:
        console.print(f"  min core  {row.min_core}")

    for need in row.needs or []:
        console.print(f"  needs     {need}")


@app.command("install")
def install(
    slug: str = typer.Argument(..., help="Plugin slug from an index"),
    package: str | None = typer.Option(
        None,
        "--package",
        help="PyPI name or pip spec to install instead of asking an index",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Do not ask"),
) -> None:
    """Install a plugin into this CLI's environment and enable it."""
    state = PluginState.load()
    row = IndexEntry(slug=slug, pypi=package) if package else lookup(state, slug)[1]
    pip = PipInstaller()

    console.print(
        f"install [bold]{row.spec}[/bold] with pip into {pip.target or sys.executable}"
    )

    for need in row.needs or []:
        console.print(f"  needs {need}")

    if not row.verified and not package:
        console.print("  not verified by the index: read the code before trusting it")

    if not yes and not typer.confirm("continue?", default=False):
        raise typer.Exit(1)

    pip.install(row.spec)
    registry.reset()
    installed = registry.installed()

    try:
        loaded = installed.get(slug)
    except PluginError:
        console.print(
            f"installed {row.spec}, but nothing registered the slug {slug!r}; "
            "check the package's entry points"
        )

        raise typer.Exit(1)

    state.record(slug, loaded.version, loaded.package)
    state.set_enabled(slug, True)
    console.print(f"[green]ok[/green] {slug} {loaded.version} enabled")


@app.command("remove")
def remove(slug: str) -> None:
    """Uninstall a plugin's package. Running MCP servers see it go on their next start."""
    loaded = registry.installed().get(slug)

    if not loaded.package:
        raise PluginError(f"plugin {slug} has no package to uninstall")

    PipInstaller().uninstall(loaded.package)
    PluginState.load().forget(slug)
    registry.reset()
    console.print(f"[green]ok[/green] {slug} removed")


@app.command("enable")
def enable(slug: str) -> None:
    """Switch a plugin on: its tools answer, its overlays and targets show, its hooks run."""
    registry.installed().enable(slug)
    console.print(f"[green]ok[/green] {slug} enabled")


@app.command("disable")
def disable(slug: str) -> None:
    """Switch a plugin off without uninstalling it."""
    registry.installed().disable(slug)
    console.print(f"[green]ok[/green] {slug} disabled")


index_app = typer.Typer(help="Indexes the search and install commands read.")
app.add_typer(index_app, name="index")


@index_app.command("list")
def index_list() -> None:
    for url in PluginState.load().indexes:
        console.print(url)


@index_app.command("add")
def index_add(
    url: str = typer.Argument(..., help="Base URL serving <slug>.json files"),
) -> None:
    PluginState.load().add_index(url)
    console.print(f"[green]ok[/green] {url}")
