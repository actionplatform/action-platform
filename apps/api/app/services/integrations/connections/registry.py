"""Every service the platform connects with OAuth that is not a code host, by kind."""

from action_platform.core.exception import ProviderError
from app.core.abc import ConnectionProvider
from app.services.integrations.connections.sentry import SentryProvider


class ConnectionProviders:
    def __init__(self, *providers: ConnectionProvider) -> None:
        self.by_kind = {p.kind: p for p in providers}

    def __contains__(self, kind: object) -> bool:
        return kind in self.by_kind

    def __iter__(self):
        return iter(self.by_kind.values())

    def get(self, kind: str) -> ConnectionProvider:
        provider = self.by_kind.get(kind)

        if provider is None:
            raise ProviderError(f"unknown service: {kind}")

        return provider


def connection_providers() -> ConnectionProviders:
    return ConnectionProviders(SentryProvider())
