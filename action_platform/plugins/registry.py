"""Installed plugins: found through the `action_platform.plugins` entry-point group, switched on and off by `plugins.json`, handed the MCP server and the CLI to register on, and told when something happened."""

from __future__ import annotations

import functools
import importlib
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from action_platform.abc.plugin import Plugin, Surface
from action_platform.core.wiring import wired
from action_platform.core.exception import ActionPlatformError
from action_platform.logging import logger
from action_platform.plugins.options import FileOptions, Options
from action_platform.plugins.state import PluginState

if TYPE_CHECKING:
    from action_platform.core.context import Context, DeployResult, PRRef

GROUP = "action_platform.plugins"


class PluginError(ActionPlatformError):
    """A plugin that cannot be loaded, or a slug nobody installed."""


@dataclass
class Loaded:
    plugin: Plugin
    package: str = ""
    version: str = ""

    @property
    def slug(self) -> str:
        return self.plugin.slug


class PluginTools:
    """The `mcp` a plugin registers on: every tool comes out as `<slug>_<name>` (hyphens in the slug become underscores — MCP clients accept `[A-Za-z0-9_-]` only) through the server's own decorator (schemas, readable errors) and refuses to run while the plugin is disabled."""

    def __init__(
        self, mcp: Any, slug: str, plugins: "Plugins", decorator: Callable
    ) -> None:
        self.mcp = mcp
        self.slug = slug
        self.plugins = plugins
        self.decorator = decorator
        self.prefix = slug.replace("-", "_")

    def tool(self, **options: Any) -> Callable:
        def decorate(fn: Callable) -> Callable:
            @functools.wraps(fn)
            def guarded(*args: Any, **kwargs: Any) -> Any:
                if not self.plugins.is_enabled(self.slug):
                    raise PluginError(
                        f"plugin {self.slug} is disabled: action-platform plugin enable {self.slug}"
                    )

                return fn(*args, **kwargs)

            options.setdefault("name", f"{self.prefix}_{fn.__name__}")

            return self.decorator(self.mcp, **options)(guarded)

        return decorate

    def prompt(self, **options: Any) -> Callable:
        return self.mcp.prompt(**options)


class Slots:
    """The wiring as one plugin sees it: `replace` records who did it, so disabling the plugin undoes exactly its replacements."""

    def __init__(self, slug: str) -> None:
        self.slug = slug

    def replace(self, slot: str, impl: type) -> None:
        wired.replace(slot, impl, by=self.slug)

    def resolve(self, slot: str) -> type:
        return wired.resolve(slot)

    def slots(self) -> list[str]:
        return wired.slots()

    def __getattr__(self, slot: str) -> Any:
        if slot.startswith("_"):
            raise AttributeError(slot)

        return wired.resolve(slot)


class Plugins:
    def __init__(
        self, found: list[Loaded], state: Optional[PluginState] = None
    ) -> None:
        self.found = found
        self.state = state or PluginState.load()
        self.seen_stamp = self.state.stamp()
        self.options_factory: Callable[[str], Options] = _options_factory

    @classmethod
    def discover(cls, state: Optional[PluginState] = None) -> "Plugins":
        return cls(cls.find(), state)

    @staticmethod
    def find(known: Optional[set[str]] = None) -> list[Loaded]:
        """Every plugin the entry points name; `known` skips slugs already loaded, so a refresh brings only what was installed since."""
        found: list[Loaded] = []
        importlib.invalidate_caches()

        for ep in entry_points(group=GROUP):
            if known is not None and ep.name in known:
                continue

            try:
                loaded = ep.load()
                plugin = loaded() if isinstance(loaded, type) else loaded
            except Exception as e:
                logger.warning(f"plugin {ep.name} failed to load: {e}")

                continue

            if not isinstance(plugin, Plugin):
                logger.warning(
                    f"plugin {ep.name} is not an action_platform.abc.Plugin; skipped"
                )

                continue

            dist = getattr(ep, "dist", None)
            found.append(
                Loaded(
                    plugin,
                    getattr(dist, "name", "") or "",
                    getattr(dist, "version", "") or "",
                )
            )

        return found

    def refresh(self) -> list[Loaded]:
        """Reread `plugins.json` and pick up packages installed since discovery — the Jenkins move: a new plugin joins the running process, registered on the same surfaces. Already-loaded code stays as it is; an upgrade or a removal takes a restart."""
        self.state = PluginState.load(self.state.file)
        self.seen_stamp = self.state.stamp()
        new = self.find(known={row.slug for row in self.found})
        self.found.extend(new)

        for row in new:
            if self.is_enabled(row.slug):
                self._register(row)

        return new

    def stale(self) -> bool:
        return self.state.stamp() != self.seen_stamp

    def get(self, slug: str) -> Loaded:
        for row in self.found:
            if row.slug == slug:
                return row

        installed = ", ".join(sorted(r.slug for r in self.found)) or "none"

        raise PluginError(f"no plugin {slug!r} installed (installed: {installed})")

    def is_enabled(self, slug: str) -> bool:
        return self.state.enabled(slug)

    def enable(self, slug: str) -> None:
        """Switch on and register again, so the slots the plugin replaces come back."""
        row = self.get(slug)
        self.state.set_enabled(slug, True)
        self.seen_stamp = self.state.stamp()
        self._register(row)

    def disable(self, slug: str) -> None:
        """Switch off: tools refuse, hooks skip, and every slot the plugin replaced goes back to the core's class."""
        self.get(slug)
        self.state.set_enabled(slug, False)
        self.seen_stamp = self.state.stamp()

        for name, by in wired.origins().items():
            if by == slug:
                wired.restore(name)

    def enabled(self) -> list[Loaded]:
        return [row for row in self.found if self.is_enabled(row.slug)]

    def disabled_packages(self) -> set[str]:
        """Distributions whose deploy targets, CI runners and overlays must stay out while their plugin is off."""
        return {
            row.package
            for row in self.found
            if row.package and not self.is_enabled(row.slug)
        }

    def rows(self) -> list[dict]:
        return [
            {
                "slug": row.slug,
                "package": row.package,
                "version": row.version,
                "enabled": self.is_enabled(row.slug),
                "description": row.plugin.description,
                "min_core": row.plugin.min_core,
                "needs": list(row.plugin.needs),
                "overlays": row.plugin.overlays is not None,
                "replaces": sorted(
                    slot for slot, by in wired.origins().items() if by == row.slug
                ),
            }
            for row in sorted(self.found, key=lambda r: r.slug)
        ]

    def register(
        self, mcp: Any = None, cli: Any = None, decorator: Optional[Callable] = None
    ) -> None:
        """Hand every enabled plugin the surfaces this process has: the MCP server with its tool decorator, the Typer app, and the core's wiring."""
        self._mcp, self._cli, self._decorator = mcp, cli, decorator

        for row in self.enabled():
            self._register(row)

    def _register(self, row: Loaded) -> None:
        mcp = getattr(self, "_mcp", None)
        decorator = getattr(self, "_decorator", None)
        surface = Surface(
            core=Slots(row.slug),
            options=self.options_for(row.slug),
            mcp=PluginTools(mcp, row.slug, self, decorator)
            if mcp is not None and decorator is not None
            else None,
            cli=getattr(self, "_cli", None),
        )

        try:
            row.plugin.register(surface)
        except Exception as e:
            logger.warning(f"plugin {row.slug} failed to register: {e}")

    def options_for(self, slug: str) -> Options:
        """The plugin's option store — the file backend unless the host process installed another (the API's table)."""
        return self.options_factory(slug)

    def overlay_roots(self) -> list[tuple[str, Path]]:
        """(slug, directory) for every enabled plugin that ships overlays; the directory holds an `index.json` and `cloud/<name>/`."""
        rows: list[tuple[str, Path]] = []

        for row in self.enabled():
            root = row.plugin.overlays

            if root is None:
                continue

            if not (Path(root) / "index.json").exists():
                logger.warning(f"plugin {row.slug}: overlays without index.json")

                continue

            rows.append((row.slug, Path(root)))

        return rows

    def after_release(self, ctx: "Context") -> None:
        self._each("after_release", ctx)

    def after_deploy(self, results: list["DeployResult"]) -> None:
        self._each("after_deploy", results)

    def after_pull_request(self, ref: "PRRef") -> None:
        self._each("after_pull_request", ref)

    def _each(self, hook: str, payload: Any) -> None:
        for row in self.enabled():
            try:
                getattr(row.plugin, hook)(payload)
            except Exception as e:
                logger.warning(f"plugin {row.slug}.{hook} failed: {e}")


_current: Optional[Plugins] = None
_options_factory: Callable[[str], Options] = FileOptions


def use_options(factory: Callable[[str], Options]) -> None:
    """The host process names where plugin options live — the API hands over its table; it holds across rediscoveries."""
    global _options_factory

    _options_factory = factory

    if _current is not None:
        _current.options_factory = factory


def installed() -> Plugins:
    """The plugins of this process — discovered once, refreshed whenever `plugins.json` changed under it (another process installed or switched something)."""
    global _current

    if _current is None:
        _current = Plugins.discover()
    elif _current.stale():
        _current.refresh()

    return _current


def reset() -> None:
    global _current

    _current = None
