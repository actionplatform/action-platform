"""Which projects the API knows about.

A JSON file under the user's config dir, one entry per local checkout. The
web app adds and removes entries; ids are stable so links survive a rename.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from ulid import ULID

from action_platform.core.exception import ActionPlatformError
from action_platform.settings import settings


def registry_path() -> Path:
    base = os.environ.get("AP_HOME") or os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) / "action-platform" if base else Path.home() / ".action-platform"

    return root / "projects.json"


@dataclass
class Entry:
    id: str
    name: str
    path: str


class Registry:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or registry_path()

    def _load(self) -> list[Entry]:
        if not self.path.exists():
            return []

        data = json.loads(self.path.read_text() or "[]")

        return [Entry(**row) for row in data]

    def _save(self, rows: list[Entry]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([asdict(r) for r in rows], indent=2) + "\n")

    def list(self) -> list[Entry]:
        return self._load()

    def get(self, id: str) -> Entry:
        for row in self._load():
            if row.id == id:
                return row

        raise ActionPlatformError(f"project {id} is not registered")

    def add(self, path: Path) -> Entry:
        path = path.resolve()

        if not (path / settings.CONFIG_FILE).exists():
            raise ActionPlatformError(f"{settings.CONFIG_FILE} not found in {path}")

        rows = self._load()

        for row in rows:
            if Path(row.path) == path:
                return row

        entry = Entry(id=str(ULID()).lower(), name=path.name, path=str(path))
        rows.append(entry)
        self._save(rows)

        return entry

    def remove(self, id: str) -> None:
        rows = [r for r in self._load() if r.id != id]
        self._save(rows)
