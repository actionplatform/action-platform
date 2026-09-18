"""What several contexts need about one app: the repository it points at, its stored configuration, the tags of its clone."""

from __future__ import annotations

from action_platform.core.config import Config
from action_platform.core.exception import ActionPlatformError
from app.core.db.models import App
from app.core.shared.urls import GitUrl
from app.repositories.configuration.config_store import ConfigStore
from app.repositories.workspace.registry import Registry
from app.services.workspace.state import GitStateService


class AppContext:
    def __init__(self, registry: Registry, configs: ConfigStore | None = None) -> None:
        self.registry = registry
        self.configs = configs or ConfigStore(registry.store.database)

    def repo_of(self, app: App) -> str:
        data = self.configs.get(app.registry_id) or {}
        repo = (data.get("source_host") or {}).get("repo")

        if repo:
            return str(repo)

        try:
            return GitUrl(self.registry.get(app.registry_id).url).repo
        except ActionPlatformError:
            return ""

    def config_of(self, app: App) -> Config:
        return self.configs.config_of(app.registry_id)

    def tags_of(self, app: App) -> list[dict]:
        try:
            return GitStateService(self.registry).releases(app.registry_id)
        except ActionPlatformError:
            return []
