"""Plugins on the hosted platform, the Jenkins way: install from the index into the plugins volume without a restart, switch on and off at once, and mark what needs a restart — an upgrade or a removal."""

from __future__ import annotations

import os
import threading
from typing import Any, Optional

from action_platform.core.exception import ActionPlatformError
from action_platform.plugins import PluginError, PluginState, registry
from action_platform.plugins.installer import IndexEntry, PipInstaller
from action_platform.settings import settings
from app.services.catalog.published import plugins_index
from app.services.plugins.catalog import PluginsCatalog
from app.services.plugins.options import DbOptions
from app.services.jobs.queue import JobQueue

INSTALL = "install_plugin"
REMOVE = "remove_plugin"
RESTART = "restart"


class PluginManager:
    def __init__(
        self, queue: Optional[JobQueue] = None, database: Optional[Any] = None
    ) -> None:
        self.queue = queue
        self.database = database

    def options(self, slug: str, organization_id: str = "") -> DbOptions:
        if self.database is None:
            raise ActionPlatformError("no database")

        return DbOptions(self.database, slug, organization_id)

    def catalog(self) -> dict:
        return PluginsCatalog().rows()

    def entry(self, slug: str) -> IndexEntry:
        """The index row for `slug` — the hosted platform installs only what the index verified."""
        published = plugins_index.get() or {}

        for row in published.get("plugins") or []:
            if row.get("name") == slug:
                entry = IndexEntry.from_row(row)

                if not entry.verified:
                    raise PluginError(
                        f"plugin {slug} is not verified by the index; the hosted platform installs verified plugins only"
                    )

                return entry

        raise PluginError(f"no plugin {slug!r} in the index")

    def ready(self) -> None:
        if settings.PLUGINS_DIR is None:
            raise ActionPlatformError(
                "AP_PLUGINS_DIR is not set: mount a volume and point the API and the worker at it"
            )

    def enqueue_install(self, slug: str, user_id: str) -> Any:
        self.ready()
        entry = self.entry(slug)

        return self._enqueue(
            INSTALL,
            {"slug": slug, "spec": entry.spec, "by": user_id},
            f"install:{slug}",
        )

    def enqueue_remove(self, slug: str, user_id: str) -> Any:
        """Removes what is loaded, or what `plugins.json` remembers — a plugin that failed to load still has a package on disk."""
        self.ready()
        plugins = registry.installed()
        package = ""

        try:
            package = plugins.get(slug).package
        except PluginError:
            row = plugins.state.plugins.get(slug)

            if row is None:
                raise

            package = row.package

        return self._enqueue(
            REMOVE,
            {"slug": slug, "package": package, "by": user_id},
            f"remove:{slug}",
        )

    def enqueue_restart(self, user_id: str) -> Any:
        return self._enqueue(RESTART, {"by": user_id}, "restart")

    def _enqueue(self, kind: str, payload: dict, dedupe: str) -> Any:
        if self.queue is None:
            raise ActionPlatformError("no job queue")

        return self.queue.enqueue(kind, payload, dedupe_key=dedupe)

    def enable(self, slug: str) -> None:
        registry.installed().enable(slug)

    def disable(self, slug: str) -> None:
        registry.installed().disable(slug)

    def install(self, payload: dict) -> dict:
        """The job: pip into the volume, then load the new plugin into this process; an already-loaded one stays as it is and the restart flag goes up."""
        self.ready()
        slug, spec = payload["slug"], payload["spec"]
        plugins = registry.installed()
        before = {row.slug: row.version for row in plugins.found}
        PipInstaller(str(settings.PLUGINS_DIR)).install(spec)
        state = PluginState.load()

        if slug in before:
            state.mark_restart(slug)
            state.record(slug, spec.split("==")[-1], spec.split("==")[0])

            return {"slug": slug, "installed": spec, "restart_required": True}

        state.record(slug, "", spec.split("==")[0])
        state.set_enabled(slug, True)
        new = plugins.refresh()
        loaded = next((row for row in new if row.slug == slug), None)

        if loaded is None:
            why = registry.FAILURES.get(slug)

            raise PluginError(
                f"installed {spec}, but the plugin did not load: {why}"
                if why
                else f"installed {spec}, but nothing registered the slug {slug!r}"
            )

        state.record(slug, loaded.version, loaded.package)

        return {"slug": slug, "installed": spec, "version": loaded.version}

    def remove(self, payload: dict) -> dict:
        self.ready()
        slug, package = payload["slug"], payload["package"]
        state = PluginState.load()
        loaded = any(row.slug == slug for row in registry.installed().found)

        if package:
            PipInstaller(str(settings.PLUGINS_DIR)).uninstall(package)

        if loaded:
            state.mark_removed(slug)
        else:
            state.forget(slug)

        return {"slug": slug, "removed": package, "restart_required": loaded}

    def restart(self, payload: dict) -> dict:
        """The worker's part of a restart: answer, then leave; the orchestrator brings it back."""
        PluginState.load().clear_restart()
        exit_soon()

        return {"restarting": True}

    def restart_api(self) -> None:
        """The API's part: leave after the response; the flag is cleared by the worker, which restarts too."""
        exit_soon()


def exit_soon(delay: float = 1.0) -> None:
    """Leave the process after the current response went out; `restart: always` on the container does the rest."""
    threading.Timer(delay, lambda: os._exit(0)).start()
