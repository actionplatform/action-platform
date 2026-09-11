"""Devtool CLI entrypoint."""

import sys

from rich.console import Console

from devtool.cli.setup import app
from devtool.core.exception import DevtoolError


def main() -> None:
    try:
        app()
    except DevtoolError as e:
        Console(stderr=True).print(f"[red]error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
