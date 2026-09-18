"""The snapshot of an app: one JSON row per registry entry with what its pages read, and when it was taken."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from app.core.db.models import AppSnapshot


class SnapshotStore:
    def __init__(self, database: Any) -> None:
        self.database = database

    def get(self, registry_id: str) -> Optional[tuple[dict, datetime]]:
        with self.database.session() as s:
            row = s.get(AppSnapshot, registry_id)

            return (json.loads(row.data), row.taken_at) if row else None

    def set(self, registry_id: str, data: dict) -> None:
        with self.database.session() as s:
            row = s.get(AppSnapshot, registry_id)

            if row is None:
                row = AppSnapshot(registry_id=registry_id)
                s.add(row)

            row.data = json.dumps(data, default=str)
            s.commit()

    def delete(self, registry_id: str) -> None:
        with self.database.session() as s:
            row = s.get(AppSnapshot, registry_id)

            if row is not None:
                s.delete(row)
                s.commit()
