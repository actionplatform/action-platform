"""App › Scopes: the app's scopes as the platform keeps them, and the configuration the core sees with them. No scope, no deploy."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session as DbSession

from action_platform.core.config import Config
from action_platform.core.exception import ConfigError
from action_platform.core.scopes import CRITICALITIES, KINDS, ScopeSpec, parse_scopes
from app.core.db.models import App, Scope
from app.core.errors import Conflict, Invalid, NotFound
from app.repositories.configuration.config_store import ConfigStore
from app.repositories.scopes import ScopeStore


class ScopesService:
    def __init__(self, db: DbSession, configs: ConfigStore) -> None:
        self.db = db
        self.configs = configs
        self.store = ScopeStore(db)

    def of(self, app: App) -> list[Scope]:
        return self.store.for_app(app.id)

    def specs(self, app: App) -> list[ScopeSpec]:
        return [ScopeStore.spec_of(row) for row in self.of(app)]

    def names(self, app: App) -> list[str]:
        return [row.name for row in self.of(app)]

    def get(self, app: App, name: str) -> Scope:
        row = self.store.get(app.id, name)

        if row is None:
            names = ", ".join(self.names(app)) or "none"

            raise NotFound(f"no scope {name!r} (scopes: {names})")

        return row

    def create(self, app: App, body: dict[str, Any], user_id: Optional[str]) -> Scope:
        spec = self._spec(body)

        if self.store.get(app.id, spec.name) is not None:
            raise Conflict(f"scope {spec.name!r} exists")

        return self.store.create(app.id, spec, created_by=user_id)

    def update(self, app: App, name: str, body: dict[str, Any]) -> Scope:
        row = self.get(app, name)
        spec = self._spec({**body, "name": name})

        return self.store.update(row, spec)

    def delete(self, app: App, name: str, live: bool) -> None:
        row = self.get(app, name)

        if live:
            raise Conflict(f"a deploy to {name} is running; wait for it to finish")

        self.store.delete(row)

    def configured(self, config: Config, app: App) -> Config:
        """The core's Config with the platform's scopes in place of whatever platform.toml says."""
        config._scopes_spec = [ScopeStore.as_toml(spec) for spec in self.specs(app)]

        return config

    def _spec(self, body: dict[str, Any]) -> ScopeSpec:
        name = str(body.get("name") or "").strip()

        if not name:
            raise Invalid("name is required")

        item = {
            "name": name,
            "kind": body.get("kind") or "web",
            "criticality": body.get("criticality") or "low",
        }

        try:
            return parse_scopes({"scopes": [item]})[0]
        except ConfigError as e:
            raise Invalid(str(e)) from e

    @staticmethod
    def vocabulary() -> dict[str, list[str]]:
        return {"kinds": list(KINDS), "criticalities": list(CRITICALITIES)}
