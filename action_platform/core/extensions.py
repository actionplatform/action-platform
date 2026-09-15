"""The port through which the core reaches whatever extends it — hooks after a release, a deploy or a pull request; packages switched off; overlay directories. The plugin registry provides it from the package's composition root; the core never imports the registry."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional, Protocol

if TYPE_CHECKING:
    from action_platform.core.context import Context, DeployResult, PRRef


class Extensions(Protocol):
    def after_release(self, ctx: "Context") -> None: ...

    def after_deploy(self, results: list["DeployResult"]) -> None: ...

    def after_pull_request(self, ref: "PRRef") -> None: ...

    def disabled_packages(self) -> set[str]: ...

    def overlay_roots(self) -> list[tuple[str, Path]]: ...


class NoExtensions:
    """What the core gets until something provides more: nothing hooked, nothing disabled, no overlays."""

    def after_release(self, ctx: "Context") -> None:
        return None

    def after_deploy(self, results: list["DeployResult"]) -> None:
        return None

    def after_pull_request(self, ref: "PRRef") -> None:
        return None

    def disabled_packages(self) -> set[str]:
        return set()

    def overlay_roots(self) -> list[tuple[str, Path]]:
        return []


_provider: Optional[Callable[[], Extensions]] = None


def provide(provider: Callable[[], Extensions]) -> None:
    """Name what answers `current()` — called once by the package's composition root."""
    global _provider

    _provider = provider


def current() -> Extensions:
    return _provider() if _provider is not None else NoExtensions()
