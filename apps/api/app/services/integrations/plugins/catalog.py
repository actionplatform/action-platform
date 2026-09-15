"""The plugins marketplace: what the plugins index publishes, and which of them this platform runs."""

from action_platform.plugins import registry
from action_platform.settings import settings
from app.services.templates.published import plugins_index as published_plugins


class PluginsCatalog:
    def rows(self) -> dict:
        """The marketplace: what the plugins index publishes, and which of them this platform runs."""
        published = published_plugins.get() or {}
        plugins = registry.installed()
        installed = {row["slug"]: row for row in plugins.rows()}
        remembered = plugins.state.plugins
        pending = set(plugins.state.restart_pending())
        rows = []

        for row in published.get("plugins") or []:
            slug = row.get("name") or ""
            here = installed.get(slug)
            kept = remembered.get(slug)
            removed = bool(kept and kept.removed)
            error = (
                registry.FAILURES.get(slug)
                if here is None and kept and not removed
                else None
            )
            rows.append(
                {
                    "slug": slug,
                    "description": row.get("description") or "",
                    "author": row.get("author") or "",
                    "verified": bool(row.get("verified")),
                    "repo": row.get("repo") or "",
                    "pypi": row.get("pypi") or "",
                    "latest": row.get("latest") or "",
                    "min_core": row.get("min_core") or "",
                    "needs": list(row.get("needs") or []),
                    "tags": list(row.get("tags") or []),
                    "installed": (here is not None or kept is not None) and not removed,
                    "installed_version": here["version"]
                    if here
                    else (kept.version if kept else None),
                    "enabled": bool(here and here["enabled"]) and not removed,
                    "removed": removed,
                    "restart_pending": slug in pending,
                    "error": error,
                }
            )

        return {
            "plugins": rows,
            "index": settings.PLUGINS_INDEX_URL,
            "hosted": settings.PLUGINS_DIR is not None,
            "restart_pending": sorted(pending),
        }
