"""Pending edits of an app: files changed through the API and not committed yet, kept in the database so every instance and worker applies the same ones."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import delete, select

from app.core.db.models import Draft
from action_platform.core.flow.repository import Repository


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DraftStore:
    def __init__(self, database) -> None:
        self.database = database

    def files(self, registry_id: str) -> dict[str, Optional[str]]:
        with self.database.session() as s:
            rows = s.scalars(
                select(Draft)
                .where(Draft.registry_id == registry_id)
                .order_by(Draft.path)
            )

            return {d.path: d.content for d in rows}

    def paths(self, registry_id: str) -> list[str]:
        return sorted(self.files(registry_id))

    def replace(self, registry_id: str, files: dict[str, Optional[str]]) -> None:
        with self.database.session() as s:
            s.execute(delete(Draft).where(Draft.registry_id == registry_id))

            for path, content in files.items():
                s.add(
                    Draft(
                        registry_id=registry_id,
                        path=path,
                        content=content,
                        updated_at=now(),
                    )
                )

    def clear(self, registry_id: str) -> None:
        self.replace(registry_id, {})

    def capture(self, registry_id: str, root: Path) -> list[str]:
        """Record everything the working tree has that HEAD does not: the draft becomes exactly the current diff."""
        files: dict[str, Optional[str]] = {}

        for relative in Repository(root).changed_files():
            path = root / relative

            if path.is_file():
                try:
                    files[relative] = path.read_text()
                except UnicodeDecodeError:
                    continue
            else:
                files[relative] = None

        self.replace(registry_id, files)

        return sorted(files)

    def overlay(self, registry_id: str, root: Path) -> list[str]:
        """Write the draft on top of a clean checkout."""
        files = self.files(registry_id)

        for relative, content in files.items():
            path = root / relative

            if content is None:
                if path.exists():
                    path.unlink()

                continue

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

        return sorted(files)
