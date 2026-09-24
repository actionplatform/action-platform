"""A `.env` next to where the command runs fills in variables the shell did not set — never overriding it."""

import os
from pathlib import Path


class DotEnv:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> dict[str, str]:
        if not self.path.is_file():
            return {}

        values: dict[str, str] = {}

        for raw in self.path.read_text().splitlines():
            line = raw.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, _, value = line.partition("=")
            key = key.strip().removeprefix("export ").strip()
            value = value.strip()

            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]

            values[key] = value

        return values

    def apply(self) -> list[str]:
        applied = []

        for key, value in self.read().items():
            if key not in os.environ:
                os.environ[key] = value
                applied.append(key)

        return applied


def load(path: Path | None = None) -> list[str]:
    """Apply `path` (default: `.env` in the working directory); an entry point calls it before it reads a setting — importing never does."""
    return DotEnv(path or Path.cwd() / ".env").apply()
