"""Which callable runs which job kind — filled by the contexts that own the kinds, read by the worker. A context registers at import; the worker imports the contexts."""

from __future__ import annotations

from typing import Any, Callable

Handler = Callable[[dict[str, Any]], Any]
Factory = Callable[["JobServices"], Handler]


class JobServices:
    """What a handler factory receives: the database, the sealer, the registry of apps."""

    def __init__(self, database: Any, sealer: Any, registry: Any) -> None:
        self.database = database
        self.sealer = sealer
        self.registry = registry


_factories: dict[str, Factory] = {}


def register(kind: str, factory: Factory) -> None:
    _factories[kind] = factory


def kinds() -> list[str]:
    return sorted(_factories)


def handlers(services: JobServices) -> dict[str, Handler]:
    return {kind: factory(services) for kind, factory in _factories.items()}
