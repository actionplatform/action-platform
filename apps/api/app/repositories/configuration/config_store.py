"""The app's configuration — the tables of platform.toml — as the platform keeps it: the database is the source of truth between syncs; a platform.toml that changed in the repository since it was last imported or exported wins on the next sync."""

from __future__ import annotations

import hashlib
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

    def set(
        self, registry_id: str, data: dict, file_hash: Optional[str] = None
    ) -> dict:
        clean = {k: v for k, v in data.items() if k in TABLES}

        with self.database.session() as s:
            row = s.get(AppConfig, registry_id)

            if row is None:
                row = AppConfig(registry_id=registry_id)
                s.add(row)

            row.data = json.dumps(clean)

            if file_hash is not None:
                row.file_hash = file_hash

            s.commit()

        return clean

    def merge(self, registry_id: str, root: Path, **tables: dict) -> dict:
        """An overlay or a service wrote tables into the clone's platform.toml: the record takes them, and the file as it is now counts as seen."""
        data = {**self.resolve(registry_id, root), **tables}
        file = root / settings.CONFIG_FILE
        digest = _digest(file.read_text()) if file.exists() else None

        return self.set(registry_id, data, digest)

    def adopt(self, registry_id: str, root: Path) -> bool:
        """On sync: when the clone's platform.toml differs from the one last imported or exported, it replaces what the platform keeps. Returns whether it did."""
        file = root / settings.CONFIG_FILE

        if not file.exists():
            return False

        text = file.read_text()
        digest = _digest(text)

        with self.database.session() as s:
            row = s.get(AppConfig, registry_id)
            seen = row.file_hash if row else None
            stored = json.loads(row.data) if row else None

        if seen == digest:
            return False

        data = tomllib.loads(text)

        if stored is not None and _tables(data) == _tables(stored):
            self.set(registry_id, stored, digest)

            return False

        self.set(registry_id, data, digest)

        return True

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

        text = file.read_text()

        return self.set(registry_id, tomllib.loads(text), _digest(text))

    def config(self, registry_id: str, root: Path) -> Config:
        return Config.from_dict(self.resolve(registry_id, root))

    def config_of(self, registry_id: str) -> Config:
        """The stored configuration without a clone — empty when the app was never opened."""
        return Config.from_dict(self.get(registry_id) or {})

    def render(self, registry_id: str, root: Path) -> str:
        return dump_toml(self.resolve(registry_id, root))

    def export(self, registry_id: str, root: Path) -> Path:
        """Write the mirror: platform.toml in the clone from what the platform keeps; the file written is the one the next sync compares against."""
        file = root / settings.CONFIG_FILE
        text = self.render(registry_id, root)
        file.write_text(text)

        with self.database.session() as s:
            row = s.get(AppConfig, registry_id)

            if row is not None:
                row.file_hash = _digest(text)
                s.commit()

        return file


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _tables(data: dict) -> dict:
    return {k: v for k, v in data.items() if k in TABLES}
