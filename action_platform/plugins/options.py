"""Where a plugin keeps what it needs to remember — WordPress's options table, one namespace per plugin: `surface.options.get("channel")`, `set`, `delete`, `all`. A JSON file per plugin on a machine; a table on the hosted platform, which hands the registry its own backend."""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class Credential:
    """A live token of one of the organization's connections, for the call that asked: `api_url` is where the provider's API lives (None for the public one), `scopes` what the token was granted when the provider says (None when it does not), `app` the GitHub App slug when the token comes from one."""

    kind: str
    token: str
    login: str = ""
    api_url: Optional[str] = None
    scopes: Optional[tuple[str, ...]] = None
    app: Optional[str] = None

    def __repr__(self) -> str:
        return f"Credential(kind={self.kind!r}, login={self.login!r})"


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

    def credential(self, kind: str) -> Optional[Credential]:
        """The organization's connection of `kind`, when the plugin declared it in `connections` and the organization connected it; None on a machine."""
        return None


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
