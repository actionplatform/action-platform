"""The plugin options store backed by the database — what the file backend is on a machine."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import delete, select

from action_platform.plugins import Options
from app.core.db.database import Database
from app.core.db.models import PluginOption


class DbOptions(Options):
    def __init__(self, database: Database, slug: str) -> None:
        self.database = database
        self.slug = slug

    def get(self, key: str, default: Any = None) -> Any:
        with self.database.session() as s:
            row = s.get(PluginOption, (self.slug, key))

            return json.loads(row.value) if row else default

    def set(self, key: str, value: Any) -> None:
        with self.database.session() as s:
            row = s.get(PluginOption, (self.slug, key))

            if row is None:
                row = PluginOption(plugin=self.slug, key=key)
                s.add(row)

            row.value = json.dumps(value)
            s.commit()

    def delete(self, key: str) -> None:
        with self.database.session() as s:
            s.execute(
                delete(PluginOption).where(
                    PluginOption.plugin == self.slug, PluginOption.key == key
                )
            )
            s.commit()

    def all(self) -> dict[str, Any]:
        with self.database.session() as s:
            rows = s.scalars(
                select(PluginOption).where(PluginOption.plugin == self.slug)
            ).all()

            return {row.key: json.loads(row.value) for row in rows}
