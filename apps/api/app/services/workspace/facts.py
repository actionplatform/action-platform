"""What the clone says about an app, read in one place: the detail the app page shows and the manifest the platform renders next to the file. Both the snapshot and the app service ask here, so neither needs the other."""

from __future__ import annotations

import tomllib
from pathlib import Path

from action_platform.core.flow.repository import Repository
from action_platform.settings import settings
from app.repositories.configuration.config_store import ConfigStore
from app.repositories.workspace.registry import Registry
from app.services.workspace.checkout import Workspaces
from app.services.workspace.manifest import AppManifest


def same_toml(a: str, b: str) -> bool:
    try:
        return tomllib.loads(a) == tomllib.loads(b)
    except tomllib.TOMLDecodeError:
        return False


class AppFacts:
    def __init__(self, registry: Registry, configs: ConfigStore | None = None) -> None:
        self.registry = registry
        self.configs = configs or ConfigStore(registry.store.database)

    def root(self, id: str) -> Path:
        return Workspaces(self.registry).checkout(id)[1]

    def detail(self, id: str) -> dict:
        entry, root = Workspaces(self.registry).checkout(id)
        info = AppManifest(root, self.configs.resolve(id, root) or None).as_dict()
        info["id"] = id
        info["url"] = entry.url
        info["default_branch"] = entry.default_branch

        repo = Repository(root)
        info["branch"] = repo.branch if repo.exists() else entry.checked_out
        info["latest_tag"] = repo.latest_tag() if repo.exists() else None
        info["clean"] = not self.registry.drafts.paths(id)

        return info

    def manifest(self, id: str) -> dict:
        root = self.root(id)
        content = self.configs.render(id, root)
        file = root / settings.CONFIG_FILE
        mirrored = file.exists() and same_toml(file.read_text(), content)

        return {"content": content, "mirrored": mirrored}
