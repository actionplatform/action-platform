"""What the app pages show, read from a row instead of a clone: taken from the workspace after every change the platform makes, and on first sight."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from action_platform.core.exception import ActionPlatformError
from app.core.errors import NotFound
from app.repositories.configuration.config_store import ConfigStore
from app.repositories.workspace.registry import Registry
from app.repositories.workspace.snapshots import SnapshotStore
from app.services.workspace.state import GitStateService

COMMITS = 50


class SnapshotService:
    def __init__(self, registry: Registry, configs: ConfigStore | None = None) -> None:
        self.registry = registry
        self.configs = configs or ConfigStore(registry.store.database)
        self.store = SnapshotStore(registry.store.database)
        self.state = GitStateService(registry)

    def take(self, id: str) -> dict:
        """Read everything from the clone once and keep it."""
        from app.services.configuration.service import ConfigurationService
        from app.services.projects.apps import AppService

        detail = AppService(self.registry, self.configs).detail(id)
        manifest = ConfigurationService(self.registry, self.configs).manifest(id)
        data = {
            "detail": detail,
            "gitflow": self.state.gitflow(id),
            "commits": self.state.commits(id, COMMITS),
            "branches": self.state.branches(id),
            "tags": self.state.tags(id),
            "releases": self.state.releases(id),
            "manifest": manifest,
        }
        self.store.set(id, data)

        return data

    def forget(self, id: str) -> None:
        self.store.delete(id)

    def read(self, id: str) -> tuple[dict, Optional[datetime]]:
        """The snapshot, taken now when the app has none yet."""
        found = self.store.get(id)

        if found is None:
            try:
                return self.take(id), None
            except ActionPlatformError:
                raise
            except FileNotFoundError as e:
                raise NotFound(str(e)) from e

        return found

    def detail(self, id: str) -> dict:
        data, taken = self.read(id)
        out: dict[str, Any] = dict(data["detail"])
        out["clean"] = not self.registry.drafts.paths(id)
        out["snapshot_at"] = taken

        return out

    def gitflow(self, id: str) -> dict:
        return self.read(id)[0]["gitflow"]

    def commits(self, id: str, limit: int) -> list[dict]:
        return self.read(id)[0]["commits"][:limit]

    def branches(self, id: str) -> list[dict]:
        return self.read(id)[0]["branches"]

    def tags(self, id: str) -> list[str]:
        return self.read(id)[0]["tags"]

    def releases(self, id: str) -> list[dict]:
        return self.read(id)[0]["releases"]

    def manifest(self, id: str) -> dict:
        return self.read(id)[0]["manifest"]
