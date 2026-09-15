"""What every app module shares: the registry."""

from action_platform_api.repositories.registry import Registry


class AppsBase:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry
