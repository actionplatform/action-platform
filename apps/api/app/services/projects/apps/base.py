"""What every app module shares: the registry and the platform's record of each app's configuration."""

from __future__ import annotations

from app.repositories.configuration.config_store import ConfigStore
from app.repositories.workspace.registry import Registry


class AppsBase:
    def __init__(self, registry: Registry, configs: ConfigStore | None = None) -> None:
        self.registry = registry
        self.configs = configs or ConfigStore(registry.store.database)
