"""Finishing a service's OAuth connection: the provider's answer becomes the organization's connection of that kind."""

from typing import TYPE_CHECKING, Optional

from action_platform.core.exception import ActionPlatformError
from app.core.db.models import Organization
from app.services.integrations.connections.registry import ConnectionProviders
from app.services.integrations.hosts.connect import HostConnectError

if TYPE_CHECKING:
    from app.services.integrations.hosts.directory import IntegrationsDirectory


class ConnectionConnector:
    def __init__(
        self, writes: "IntegrationsDirectory", providers: ConnectionProviders
    ) -> None:
        self.writes = writes
        self.providers = providers

    def finish(
        self,
        org: Organization,
        kind: str,
        origin: str,
        code: str,
        user_id: Optional[str] = None,
    ) -> None:
        """Trade the code for tokens and store them. Raises HostConnectError with the problem to show."""
        app = self.writes.oauth_app(kind)
        provider = self.providers.get(kind)

        if app is None:
            raise HostConnectError(f"{provider.label} OAuth app is not configured")

        try:
            grant = provider.exchange_code(app, origin, code)
            self.writes.save_connection(
                org.id,
                kind,
                grant.login,
                grant.access,
                grant.refresh,
                grant.expires_at,
                grant.scopes,
                provider.stored_base_url(app),
                user_id,
            )
        except ActionPlatformError as e:
            raise HostConnectError(str(e)) from e
