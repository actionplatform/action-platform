"""Action Platform CLI entrypoint."""

import subprocess
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
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or e.stdout or "").strip()
        Console(stderr=True).print(
            f"[red]error:[/red] {' '.join(e.cmd)} failed"
            + (f"\n{detail}" if detail else "")
        )
        sys.exit(e.returncode or 1)
    except FileNotFoundError as e:
        if e.filename is None:
            Console(stderr=True).print(
                "[red]error:[/red] current directory no longer exists — cd somewhere real"
            )
            sys.exit(1)
        raise


if __name__ == "__main__":
    main()
