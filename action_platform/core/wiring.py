"""Every process of the core is a class looked up here by name, so a plugin can replace one — with a subclass, so the rest of the core keeps calling what it expects.

Slots: `gitflow_rules` (branch kinds, protected branches, commit format),
`gitflow` (audit, branches, pull requests, hooks), `releaser` (plan and apply
a release), `deployer` (deploy, rollback, diagnose, destroy), `readiness`
(can a release reach a stage), `installer`
(bring a repository onto the platform), `scaffolder` (generate a project,
apply clouds and services, push). Deploy targets, CI runners, source hosts,
release strategies and changelog renderers are not slots: they are named
providers picked by platform.toml.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable

from action_platform.core.exception import ActionPlatformError

HOMES = {
    "gitflow_rules": "action_platform.core.flow.gitflow",
    "gitflow": "action_platform.core.flow.workflow",
    "releaser": "action_platform.core.release.release",
    "deployer": "action_platform.core.release.deploy",
    "readiness": "action_platform.core.release.readiness",
    "installer": "action_platform.core.scaffold.installer",
    "scaffolder": "action_platform.core.scaffold.scaffolder",
}


DECLARED: dict[str, type] = {}


class WiringError(ActionPlatformError):
    """A slot nobody provides, or a replacement that is not a subclass of what it replaces."""


class Wiring:
    """Which class fills each slot. The core's classes are declared once, for every wiring; replacements belong to one wiring.

    `Wiring.default()` is the process's — the one installed plugins replace
    slots in, and the one an `ActionPlatform` uses unless handed another. A
    test builds its own `Wiring()`: nothing it provides or replaces leaks.
    """

    def __init__(self) -> None:
        self._defaults: dict[str, type] = {}
        self._overrides: dict[str, type] = {}
        self._by: dict[str, str] = {}

    @classmethod
    def default(cls) -> "Wiring":
        return wired

    def provide(self, slot: str, default: type) -> None:
        """This wiring's own default for `slot`, over the core's declaration."""
        self._defaults.setdefault(slot, default)

    def _default(self, slot: str) -> type | None:
        """The default for `slot`: this wiring's own, else the core's class, importing the module that declares it when nothing has yet."""
        if slot in self._defaults:
            return self._defaults[slot]

        if slot not in DECLARED and slot in HOMES:
            import_module(HOMES[slot])

        return DECLARED.get(slot)

    def replace(self, slot: str, impl: type, by: str = "") -> None:
        """A plugin puts `impl` — a subclass of the default — in `slot`; `by` names the plugin for `origins()`."""
        default = self._default(slot)

        if default is None:
            raise WiringError(f"no slot {slot!r} (slots: {', '.join(self.slots())})")

        if not (isinstance(impl, type) and issubclass(impl, default)):
            raise WiringError(
                f"{slot}: {impl!r} must subclass {default.__module__}.{default.__name__}"
            )

        self._overrides[slot] = impl
        self._by[slot] = by

    def restore(self, slot: str) -> None:
        self._overrides.pop(slot, None)
        self._by.pop(slot, None)

    def resolve(self, slot: str) -> type:
        if slot in self._overrides:
            return self._overrides[slot]

        default = self._default(slot)

        if default is not None:
            return default

        raise WiringError(f"no slot {slot!r}")

    def origins(self) -> dict[str, str]:
        """slot → plugin that replaced it, for every replaced slot."""
        return dict(self._by)

    def slots(self) -> list[str]:
        return sorted(set(self._defaults) | set(DECLARED) | set(HOMES))

    def __getattr__(self, slot: str) -> Callable[..., Any]:
        if slot.startswith("_"):
            raise AttributeError(slot)

        return self.resolve(slot)


wired = Wiring()


def slot(name: str) -> Callable[[type], type]:
    """`@slot("releaser")` on the core's class declares it as the default of every wiring."""

    def decorate(cls: type) -> type:
        DECLARED.setdefault(name, cls)

        return cls

    return decorate
