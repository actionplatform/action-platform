"""Provider classes by `kind`: what the source host and CI factories build from."""

from __future__ import annotations

import inspect
from typing import Any, Generic, TypeVar

from action_platform.core.exception import ConfigError

T = TypeVar("T")


class ProviderRegistry(Generic[T]):
    """Provider classes registered under their `name` (and any aliases).

    `build` hands a class only the keyword arguments its constructor takes, so
    providers with different needs share one call and a new provider is one
    `register` away — no factory to edit.

    Args:
        label (str): what the registry holds, for error messages.
    """

    def __init__(self, label: str) -> None:
        self.label = label
        self.classes: dict[str, type[T]] = {}
        self.primary: list[str] = []

    def register(self, cls: type[T], *aliases: str) -> type[T]:
        """Add `cls` under its `name` and each alias; only the name is listed as a kind."""
        name = getattr(cls, "name")

        if name not in self.primary:
            self.primary.append(name)

        for kind in (name, *aliases):
            self.classes[kind] = cls

        return cls

    def kinds(self) -> tuple[str, ...]:
        """The registered kinds, aliases left out."""
        return tuple(self.primary)

    def build(self, kind: str, **kwargs: Any) -> T:
        """An instance of the class registered for `kind`."""
        cls = self.classes.get(kind)

        if cls is None:
            raise ConfigError(
                f"unknown {self.label} kind: {kind} (available: {', '.join(self.primary)})"
            )

        accepted = inspect.signature(cls).parameters

        return cls(**{k: v for k, v in kwargs.items() if k in accepted})
