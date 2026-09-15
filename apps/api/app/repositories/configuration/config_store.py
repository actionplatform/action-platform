"""The app's configuration — the tables of platform.toml — as the platform keeps it: the database is the source of truth, the file in the clone a mirror seeded from and exported to on request."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any, Optional

from action_platform.core.config import Config
from action_platform.core.manifest.manifest import dump_toml
from action_platform.settings import settings
from app.core.db.models import AppConfig

TABLES = ("project", "source_host", "release", "deploy", "services", "components")


class ConfigStore:
    def __init__(self, database: Any) -> None:
        self.database = database

    def get(self, registry_id: str) -> Optional[dict]:
        with self.database.session() as s:
            row = s.get(AppConfig, registry_id)

            return json.loads(row.data) if row else None

    def set(self, registry_id: str, data: dict) -> dict:
        clean = {k: v for k, v in data.items() if k in TABLES}

        with self.database.session() as s:
            row = s.get(AppConfig, registry_id)

            if row is None:
                row = AppConfig(registry_id=registry_id)
                s.add(row)

            row.data = json.dumps(clean)
            s.commit()

        return clean

    def merge(self, registry_id: str, root: Path, **tables: dict) -> dict:
        data = self.resolve(registry_id, root)

        for name, value in tables.items():
            data[name] = value

        return self.set(registry_id, data)

    def delete(self, registry_id: str) -> None:
        with self.database.session() as s:
            row = s.get(AppConfig, registry_id)

            if row is not None:
                s.delete(row)
                s.commit()

    def resolve(self, registry_id: str, root: Path) -> dict:
        """The stored configuration; on first sight, what the clone's platform.toml says, remembered from then on."""
        stored = self.get(registry_id)

        if stored is not None:
            return stored

        file = root / settings.CONFIG_FILE

        if not file.exists():
            return {}

        return self.set(registry_id, tomllib.loads(file.read_text()))

    def config(self, registry_id: str, root: Path) -> Config:
        return Config.from_dict(self.resolve(registry_id, root))

    def render(self, registry_id: str, root: Path) -> str:
        return dump_toml(self.resolve(registry_id, root))

    def export(self, registry_id: str, root: Path) -> Path:
        """Write the mirror: platform.toml in the clone from what the platform keeps."""
        file = root / settings.CONFIG_FILE
        file.write_text(self.render(registry_id, root))

        return file
