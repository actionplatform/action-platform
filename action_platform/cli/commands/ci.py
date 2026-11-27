"""`action-platform ci …` — the runs, logs and queue of a CI server a plugin brings, through the CIRunner contract; JSON on stdout, the log as text."""

from __future__ import annotations

import json
import time
from typing import Any

import typer

from action_platform.plugins import ci

app = typer.Typer(help="A CI server's runs, logs and queue.", no_args_is_help=True)

Kind = typer.Option(
    "", "--kind", help="The CI server; the only one installed when empty"
)
FOLLOW_SECONDS = 2


def _print(value: Any) -> None:
    typer.echo(json.dumps(value, indent=2))


@app.command("runs")
def runs(
    job: str,
    limit: int = typer.Option(20, help="How many, newest first"),
    kind: str = Kind,
) -> None:
    """The latest runs of a job."""
    _print(ci.runs(ci.runner(kind), job, limit))


@app.command("run")
def run(
    job: str,
    number: int = typer.Argument(0, help="Run number; the latest when 0"),
    kind: str = Kind,
) -> None:
    """One run with its parameters, causes and changes."""
    _print(ci.run(ci.runner(kind), job, number))


@app.command("log")
def log(
    job: str,
    number: int,
    start: int = typer.Option(0, help="Offset to read from"),
    node: str = typer.Option("", help="One stage or step by id"),
    follow: bool = typer.Option(
        False, "--follow", "-f", help="Keep reading while the run writes"
    ),
    kind: str = Kind,
) -> None:
    """A run's log, or one stage's, window by window with secrets masked; --follow tails it until the run ends."""
    runner = ci.runner(kind)

    while True:
        chunk = ci.log(runner, job, number, start, node)
        typer.echo(chunk["text"], nl=False)
        start = chunk["next_start"]

        if chunk["more"] and chunk["text"]:
            continue

        if not (follow and chunk["more"]):
            return

        time.sleep(FOLLOW_SECONDS)


@app.command("queue")
def queue(kind: str = Kind) -> None:
    """What waits in the queue and why."""
    _print(ci.queue(ci.runner(kind)))
