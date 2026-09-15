"""What every app module shares: the registry."""

from app.repositories.registry import Registry


class AppsBase:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry
