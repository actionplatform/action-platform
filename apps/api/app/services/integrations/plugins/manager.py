"""Plugins on the hosted platform: the ones the image bundles, discovered through their entry points, and the database-backed options each organization keeps for them."""

from __future__ import annotations

from typing import Any, Optional

from action_platform.plugins import registry
from app.core.auth.crypto import Sealer
from app.core.errors import NotFound
from app.services.integrations.plugins.events import deliveries
from app.services.integrations.plugins.options import DbOptions


class PluginManager:
    def __init__(self, database: Any, sealer: Optional[Sealer] = None) -> None:
        self.database = database
        self.sealer = sealer

    def options(self, slug: str, organization_id: str = "") -> DbOptions:
        """The options of a plugin this image runs; any other slug is refused, since only a loaded plugin says which of its keys are secrets to seal."""
        if slug not in {row["slug"] for row in registry.installed().rows()}:
            raise NotFound(f"no plugin {slug!r} in this image")

        return DbOptions(self.database, slug, organization_id, self.sealer)

    def deliveries(self, slug: str, organization_id: str) -> list[dict]:
        return deliveries(self.database, slug, organization_id)

    def catalog(self) -> dict:
        plugins = registry.installed()

        return {
            "plugins": [
                {
                    "slug": row["slug"],
                    "name": row["name"],
                    "package": row["package"],
                    "version": row["version"],
                    "description": row["description"],
                    "min_core": row["min_core"],
                    "needs": row["needs"],
                    "options": row["options"],
                    "events": row["events"],
                    "error": None,
                }
                for row in plugins.rows()
            ]
            + [
                {
                    "slug": slug,
                    "name": slug,
                    "package": "",
                    "version": "",
                    "description": "",
                    "min_core": "",
                    "needs": [],
                    "options": [],
                    "error": why,
                }
                for slug, why in sorted(registry.FAILURES.items())
            ]
        }
