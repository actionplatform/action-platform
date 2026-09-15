"""What the user decided about installed plugins — enabled or not, where it came from, which indexes to search — kept in `~/.action-platform/plugins.json`."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from action_platform.settings import settings

OFFICIAL_INDEX = (
    "https://raw.githubusercontent.com/actionplatform/plugins-index/main/plugins"
)


def path() -> Path:
    """`plugins.json`: next to the installed plugins when `AP_PLUGINS_DIR` names a directory (the hosted platform's volume), under the user's config otherwise."""
    if settings.PLUGINS_DIR is not None:
        return settings.PLUGINS_DIR / "plugins.json"

    base = os.environ.get("AP_HOME") or os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) / "action-platform" if base else Path.home() / ".action-platform"

    return root / "plugins.json"


@dataclass
class Installed:
    enabled: bool = True
    version: str = ""
    source: str = "pypi"
    package: str = ""
    pending_restart: bool = False
    removed: bool = False


@dataclass
class PluginState:
    plugins: dict[str, Installed] = field(default_factory=dict)
    indexes: list[str] = field(default_factory=lambda: [OFFICIAL_INDEX])
    file: Optional[Path] = None

    @classmethod
    def load(cls, file: Optional[Path] = None) -> "PluginState":
        file = file or path()

        if not file.exists():
            return cls(file=file)

        try:
            data = json.loads(file.read_text())
        except ValueError:
            data = {}

        plugins = {
            slug: Installed(
                **{k: v for k, v in row.items() if k in Installed.__dataclass_fields__}
            )
            for slug, row in (data.get("plugins") or {}).items()
            if isinstance(row, dict)
        }
        indexes = [
            i for i in data.get("indexes") or [OFFICIAL_INDEX] if isinstance(i, str)
        ]

        return cls(plugins=plugins, indexes=indexes or [OFFICIAL_INDEX], file=file)

    def save(self) -> None:
        file = self.file or path()
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(
            json.dumps(
                {
                    "plugins": {slug: vars(row) for slug, row in self.plugins.items()},
                    "indexes": self.indexes,
                },
                indent=2,
            )
            + "\n"
        )

    def enabled(self, slug: str) -> bool:
        row = self.plugins.get(slug)

        return row.enabled if row else True

    def set_enabled(self, slug: str, value: bool) -> None:
        self.plugins.setdefault(slug, Installed()).enabled = value
        self.save()

    def record(
        self, slug: str, version: str, package: str, source: str = "pypi"
    ) -> None:
        row = self.plugins.setdefault(slug, Installed())
        row.version = version
        row.package = package
        row.source = source
        self.save()

    def forget(self, slug: str) -> None:
        self.plugins.pop(slug, None)
        self.save()

    def mark_restart(self, slug: str, value: bool = True) -> None:
        self.plugins.setdefault(slug, Installed()).pending_restart = value
        self.save()

    def mark_removed(self, slug: str) -> None:
        """The package left the disk but the code is still loaded: disabled now, forgotten by the restart that drops it."""
        row = self.plugins.setdefault(slug, Installed())
        row.enabled = False
        row.pending_restart = True
        row.removed = True
        self.save()

    def restart_pending(self) -> list[str]:
        return sorted(slug for slug, row in self.plugins.items() if row.pending_restart)

    def clear_restart(self) -> None:
        self.plugins = {
            slug: row for slug, row in self.plugins.items() if not row.removed
        }

        for row in self.plugins.values():
            row.pending_restart = False

        self.save()

    def stamp(self) -> float:
        """When the file last changed — another process compares it to know whether to rediscover."""
        file = self.file or path()

        try:
            return file.stat().st_mtime
        except OSError:
            return 0.0

    def add_index(self, url: str) -> None:
        url = url.rstrip("/")

        if url not in self.indexes:
            self.indexes.append(url)
            self.save()
