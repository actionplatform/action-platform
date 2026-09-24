from pathlib import Path

import tomllib

from action_platform.core.wiring import wired
from action_platform.core.scaffold.installer import install
from action_platform.core.exception import TemplateError
from action_platform.settings import settings
from app.repositories.configuration.config_store import ConfigStore
from app.repositories.workspace.registry import Registry
from app.schemas import SourceSpec
from app.services.templates import TemplateRepos
from app.services.workspace import Workspaces
from app.services.workspace.facts import AppFacts
from app.core.errors import Invalid


class ConfigurationService:
    def __init__(self, registry: Registry, configs: ConfigStore | None = None) -> None:
        self.registry = registry
        self.configs = configs or ConfigStore(registry.store.database)

    def _root(self, id: str) -> Path:
        return Workspaces(self.registry).checkout(id)[1]

    def _drafted(self, id: str, root: Path) -> list[str]:
        return self.registry.drafts.capture(id, root)

    def manifest(self, id: str) -> dict:
        """The configuration the platform keeps, rendered as platform.toml; whether the clone's file matches it."""
        return AppFacts(self.registry, self.configs).manifest(id)

    def write_manifest(self, id: str, content: str) -> dict:
        """Save to the platform — nothing in the repository changes until the mirror is exported."""
        try:
            data = tomllib.loads(content)
        except tomllib.TOMLDecodeError as e:
            raise Invalid(f"invalid TOML: {e}") from e

        self.configs.set(id, data)

        return self.manifest(id)

    def export_manifest(self, id: str) -> dict:
        """Write platform.toml in the clone from what the platform keeps — a pending change to commit like any other."""
        root = self._root(id)
        self.configs.export(id, root)
        self._drafted(id, root)

        return self.manifest(id)

    def set_cloud(
        self, id: str, target: str, source: SourceSpec | str | None = None
    ) -> dict:
        repo, matrix = TemplateRepos.resolve(source)

        root = self._root(id)

        try:
            wired.scaffolder().apply_cloud(repo, matrix.cloud(target), root)
        except TemplateError as e:
            raise Invalid(str(e)) from e

        self._remember(id, root)
        self._drafted(id, root)

        return {"target": target}

    def _remember(self, id: str, root: Path) -> None:
        """An overlay wrote `[deploy]` or `[services]` into the clone's file; the platform's record takes them."""
        file = root / settings.CONFIG_FILE

        if not file.exists():
            return

        data = tomllib.loads(file.read_text())
        self.configs.merge(
            id, root, deploy=data.get("deploy", {}), services=data.get("services", {})
        )

    def add_service(
        self,
        id: str,
        name: str,
        provider: str | None,
        source: SourceSpec | str | None = None,
    ) -> dict:
        repo, matrix = TemplateRepos.resolve(source)
        service = next((s for s in matrix.services if s.name == name), None)

        if service is None:
            raise Invalid(f"unknown service: {name}")

        root = self._root(id)
        wired.scaffolder().apply_service(repo, service, root, provider=provider)
        self._remember(id, root)
        self._drafted(id, root)

        return {
            "name": name,
            "provider": provider or (service.providers[0] if service.providers else ""),
        }

    def changes(self, id: str) -> dict:
        files = self.registry.drafts.paths(id)

        return {"files": files, "clean": not files}

    def discard(self, id: str) -> dict:
        self.registry.drafts.clear(id)
        Workspaces(self.registry).refresh(id)

        return {"clean": True, "files": []}

    def install_platform(
        self, id: str, type_: str, language: str | None, ci: str | None
    ) -> dict:
        entry, root = Workspaces(self.registry).checkout(id)
        plan = install(root, type_=type_, language=language, ci=ci, name=entry.name)
        self._drafted(id, root)

        return {"installed": plan.created}
