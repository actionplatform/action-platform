"""`platform.toml` and `LAST_VERSION` of a clone, as the API answers them."""

from pathlib import Path

import tomllib
from fastapi import HTTPException

from action_platform.core.flow.repository import Repository
from action_platform.settings import settings


class AppManifest:
    def __init__(self, root: Path, data: dict | None = None) -> None:
        self.root = root
        self.path = root / settings.CONFIG_FILE
        self.data = data

    def as_dict(self) -> dict:
        """The tables the platform keeps for the app when given, the clone's file otherwise."""
        if self.data is not None:
            data = self.data
        elif self.path.exists():
            data = tomllib.loads(self.path.read_text())
        else:
            raise HTTPException(400, f"{settings.CONFIG_FILE} not found in {self.root}")

        return {
            "project": dict(data.get("project", {})),
            "source_host": data.get("source_host", {}),
            "deploy": data.get("deploy", {}),
            "release": data.get("release", {}),
            "services": data.get("services", {}),
            "last_version": self.last_version(),
        }

    def last_version(self) -> str | None:
        """What LAST_VERSION says — 0.0.0 while the repository has no version tag."""
        last = self.root / settings.LAST_VERSION_FILE

        if not last.exists():
            return None

        tagged = (
            Repository(self.root).has_tag("v[0-9]*")
            if (self.root / ".git").exists()
            else True
        )

        return last.read_text().strip() if tagged else "0.0.0"
