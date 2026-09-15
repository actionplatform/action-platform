"""Plugins on the hosted platform: the ones the image bundles, discovered through their entry points, and the database-backed options each organization keeps for them."""

from __future__ import annotations

from typing import Any

from action_platform.plugins import registry
from app.services.integrations.plugins.options import DbOptions


class PluginManager:
    def __init__(self, database: Any) -> None:
        self.database = database

    def options(self, slug: str, organization_id: str = "") -> DbOptions:
        return DbOptions(self.database, slug, organization_id)

    def catalog(self) -> dict:
        plugins = registry.installed()

        return {
            "plugins": [
                {
                    "slug": row["slug"],
                    "package": row["package"],
                    "version": row["version"],
                    "description": row["description"],
                    "min_core": row["min_core"],
                    "needs": row["needs"],
                    "error": None,
                }
                for row in plugins.rows()
            ]
            + [
                {
                    "slug": slug,
                    "package": "",
                    "version": "",
                    "description": "",
                    "min_core": "",
                    "needs": [],
                    "error": why,
                }
                for slug, why in sorted(registry.FAILURES.items())
            ]
        }
