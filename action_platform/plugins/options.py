"""Where a plugin keeps what it needs to remember — WordPress's options table, one namespace per plugin: `surface.options.get("channel")`, `set`, `delete`, `all`. A JSON file per plugin on a machine; a table on the hosted platform, which hands the registry its own backend."""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional


class Options(ABC):
    """Options"""

    slug: str

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """The value under `key`, or `default`."""

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Store `value` — anything JSON can carry."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Forget `key`; nothing happens when it is absent."""

    @abstractmethod
    def all(self) -> dict[str, Any]:
        """Every option of the plugin."""


def options_dir() -> Path:
    base = os.environ.get("AP_HOME") or os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) / "action-platform" if base else Path.home() / ".action-platform"

    return root / "plugins"


class FileOptions(Options):
    """`<dir>/<slug>.json`, rewritten whole on every change — plugins keep a handful of values, not a database."""

    def __init__(self, slug: str, root: Optional[Path] = None) -> None:
        self.slug = slug
        self.file = (root or options_dir()) / f"{slug}.json"

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.file.read_text())
        except (OSError, ValueError):
            return {}

        return data if isinstance(data, dict) else {}

    def _write(self, data: dict[str, Any]) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

    def get(self, key: str, default: Any = None) -> Any:
        return self._read().get(key, default)

    def set(self, key: str, value: Any) -> None:
        data = self._read()
        data[key] = value
        self._write(data)

    def delete(self, key: str) -> None:
        data = self._read()

        if key in data:
            del data[key]
            self._write(data)

    def all(self) -> dict[str, Any]:
        return self._read()
