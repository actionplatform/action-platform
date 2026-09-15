"""Finishing an OAuth connection: the provider's answer becomes a connected host of the organization."""

from typing import TYPE_CHECKING, Optional

from action_platform.core.exception import ActionPlatformError
from app.core.db.models import Organization
from app.services.hosts.registry import PROVIDERS

if TYPE_CHECKING:
    from app.services.directory import DirectoryWrites


class HostConnector:
    def __init__(self, writes: "DirectoryWrites") -> None:
        self.writes = writes

    def finish(
        self,
        org: Organization,
        provider: str,
        origin: str,
        code: str,
        installation_id: Optional[str],
    ) -> Optional[str]:
        """Trade the code for tokens, read who signed in, store the host. Returns the problem to show, None when connected."""
        app = self.writes.oauth_app(provider)
        host = PROVIDERS.get(provider)

        if app is None:
            return f"{host.label} OAuth app is not configured"

        try:
            access, refresh, expires_at = host.exchange_code(app, origin, code)
            login, _ = host.identity(app, access)
            owner = self._owner(provider, access, installation_id)
            self.writes.connect_oauth_host(
                org.id,
                provider,
                login,
                access,
                refresh,
                expires_at,
                host.stored_base_url(app),
                owner,
            )
        except ActionPlatformError as e:
            return str(e)

        return None

    @staticmethod
    def _owner(
        provider: str, access: str, installation_id: Optional[str]
    ) -> Optional[str]:
        if installation_id:
            return PROVIDERS.github.installation_owner(access, installation_id)

        if provider == "bitbucket":
            return PROVIDERS.bitbucket.first_workspace(access)

        return None

    def create_github_app(self, code: str) -> tuple[Optional[str], Optional[str]]:
        """Turn a manifest code into a stored GitHub App: (slug, None) when created, (None, problem) otherwise."""
        try:
            app = PROVIDERS.github.convert_manifest(code)
        except ActionPlatformError as e:
            return None, str(e)

        self.writes.save_oauth_app(
            "github", app["client_id"], app["client_secret"], None, app.get("slug")
        )

        return app.get("slug") or "created", None
