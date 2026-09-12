"""Action Platform CLI entrypoint."""

import sys

from rich.console import Console

from action_platform.cli.setup import app
from action_platform.core.exception import ActionPlatformError


def main() -> None:
    try:
        app()
    except ActionPlatformError as e:
        Console(stderr=True).print(f"[red]error:[/red] {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        if e.filename is None:
            Console(stderr=True).print(
                "[red]error:[/red] current directory no longer exists — cd somewhere real"
            )
            sys.exit(1)
        raise


if __name__ == "__main__":
    main()
