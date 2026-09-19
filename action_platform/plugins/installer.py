"""Putting a plugin's package on disk and taking it off — pip into the interpreter's environment, or into a target directory."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from action_platform.plugins.registry import PluginError
from action_platform.plugins.state import PluginState

TIMEOUT = 15


@dataclass
class IndexEntry:
    slug: str
    pypi: str
    latest: str = ""
    verified: bool = False
    description: str = ""
    repo: str = ""
    min_core: str = ""
    needs: list[str] | None = None

    @property
    def spec(self) -> str:
        return f"{self.pypi}=={self.latest}" if self.latest else self.pypi

    @classmethod
    def from_row(cls, row: dict) -> "IndexEntry":
        return cls(
            slug=row.get("name") or "",
            pypi=row.get("pypi") or "",
            latest=row.get("latest") or "",
            verified=bool(row.get("verified")),
            description=row.get("description") or "",
            repo=row.get("repo") or "",
            min_core=row.get("min_core") or "",
            needs=list(row.get("needs") or []),
        )


def fetch(url: str) -> Optional[dict]:
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as res:
            return json.loads(res.read())
    except (urllib.error.URLError, ValueError, OSError):
        return None


def lookup(state: PluginState, slug: str) -> tuple[str, IndexEntry]:
    """The index entry for `slug`, from the first index that has it."""
    for index in state.indexes:
        row = fetch(f"{index}/{slug}.json")

        if row and row.get("pypi"):
            return index, IndexEntry.from_row(row)

    raise PluginError(
        f"no plugin {slug!r} in any index ({', '.join(state.indexes)}); "
        "pass --package to install straight from PyPI"
    )


SPEC = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*(\[[A-Za-z0-9._,-]+\])?((==|>=|<=|~=|!=|>|<)[A-Za-z0-9.*+!-]+(,(==|>=|<=|~=|!=|>|<)[A-Za-z0-9.*+!-]+)*)?$"
)


class PipInstaller:
    """pip on the running interpreter; `target` set installs into that directory instead of site-packages."""

    def __init__(self, target: Optional[str] = None) -> None:
        self.target = target

    def run(self, *args: str) -> str:
        result = subprocess.run(
            [sys.executable, "-m", "pip", *args, "--disable-pip-version-check"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise PluginError(
                result.stderr.strip() or result.stdout.strip() or "pip failed"
            )

        return result.stdout

    def install(self, spec: str) -> str:
        if not SPEC.match(spec):
            raise PluginError(f"{spec!r} is not a package requirement")

        args = ["install", "--quiet", "--upgrade"]

        if self.target:
            args += ["--target", self.target]

        return self.run(*args, "--", spec)

    def uninstall(self, package: str) -> str:
        if self.target:
            return self._remove_from_target(package)

        return self.run("uninstall", "--quiet", "--yes", package)

    def _remove_from_target(self, package: str) -> str:
        """pip cannot uninstall from a --target directory; take the dist-info's RECORD as the list of what to delete."""
        root = Path(self.target or "")
        name = package.replace("-", "_").lower()
        removed = 0

        for info in root.glob("*.dist-info"):
            if not info.name.lower().startswith(name + "-"):
                continue

            record = info / "RECORD"

            for line in record.read_text().splitlines() if record.exists() else []:
                rel = line.split(",", 1)[0]
                file = root / rel

                if file.is_file():
                    file.unlink()
                    removed += 1

            for leftover in sorted(root.rglob("*"), reverse=True):
                if leftover.is_dir() and not any(leftover.iterdir()):
                    leftover.rmdir()

        return f"removed {removed} file(s)"
