"""The plugin options store backed by the database — what the file backend is on a machine. Rows belong to an organization; the empty organization holds the platform-wide defaults an organization's own values override."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import delete, select

from action_platform.plugins import Options
from app.core.db.database import Database
from app.core.db.models import PluginOption

PLATFORM = ""


class DbOptions(Options):
    def __init__(
        self, database: Database, slug: str, organization_id: str = PLATFORM
    ) -> None:
        self.database = database
        self.slug = slug
        self.organization_id = organization_id or PLATFORM

    def _key(self, key: str, organization_id: str) -> tuple[str, str, str]:
        return (organization_id, self.slug, key)

    def get(self, key: str, default: Any = None) -> Any:
        with self.database.session() as s:
            row = s.get(PluginOption, self._key(key, self.organization_id))

            if row is None and self.organization_id != PLATFORM:
                row = s.get(PluginOption, self._key(key, PLATFORM))

            return json.loads(row.value) if row else default

    def set(self, key: str, value: Any) -> None:
        with self.database.session() as s:
            row = s.get(PluginOption, self._key(key, self.organization_id))

            if row is None:
                row = PluginOption(
                    organization_id=self.organization_id, plugin=self.slug, key=key
                )
                s.add(row)

            row.value = json.dumps(value)
            s.commit()

    def delete(self, key: str) -> None:
        with self.database.session() as s:
            s.execute(
                delete(PluginOption).where(
                    PluginOption.organization_id == self.organization_id,
                    PluginOption.plugin == self.slug,
                    PluginOption.key == key,
                )
            )
            s.commit()

    def all(self) -> dict[str, Any]:
        """The organization's values over the platform's defaults."""
        with self.database.session() as s:
            rows = s.scalars(
                select(PluginOption).where(
                    PluginOption.plugin == self.slug,
                    PluginOption.organization_id.in_({PLATFORM, self.organization_id}),
                )
            ).all()

        merged = {
            r.key: json.loads(r.value) for r in rows if r.organization_id == PLATFORM
        }
        merged.update(
            {
                r.key: json.loads(r.value)
                for r in rows
                if r.organization_id == self.organization_id
            }
        )

        return merged
