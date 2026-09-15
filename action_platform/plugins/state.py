"""What the user decided about installed plugins — enabled or not, where it came from, which indexes to search — kept in `~/.action-platform/plugins.json`."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

OFFICIAL_INDEX = (
    "https://raw.githubusercontent.com/actionplatform/plugins-index/main/plugins"
)


def path() -> Path:
    base = os.environ.get("AP_HOME") or os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) / "action-platform" if base else Path.home() / ".action-platform"

    return root / "plugins.json"


@dataclass
class Installed:
    enabled: bool = True
    version: str = ""
    source: str = "pypi"
    package: str = ""


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

    def add_index(self, url: str) -> None:
        url = url.rstrip("/")

        if url not in self.indexes:
            self.indexes.append(url)
            self.save()
