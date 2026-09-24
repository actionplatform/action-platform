"""The repository behind an app on its code host."""

from __future__ import annotations

from typing import Optional

from action_platform.abc.source_host import SupportsRepoDeletion
from action_platform.core.exception import ActionPlatformError, ProviderError
from action_platform.providers.source import build_source_host
from app.core.shared.urls import GitUrl
from app.schemas import SourceCredentials
from app.services.projects.apps.base import AppsBase
from app.services.workspace.manifest import AppManifest
from app.core.errors import Conflict, ServiceError, Upstream


class AppRemote(AppsBase):
    def repository_of(self, id: str) -> Optional[tuple[str, str]]:
        """(kind, owner/name) of the remote this app was pushed to or added from; None when it has none."""
        entry, root = self.workspace(id)

        if not entry.url:
            return None

        try:
            host = AppManifest(root, self.configs.resolve(id, root) or None).as_dict()[
                "source_host"
            ]
        except ServiceError:
            host = {}

        repo = host.get("repo") or GitUrl(entry.url).repo
        kind = host.get("kind") or GitUrl(entry.url).kind

        if not repo or not kind:
            return None

        return kind, repo

    def delete_repository(self, id: str, credentials: SourceCredentials) -> str:
        """Delete the remote repository behind the app with `credentials`; returns owner/name."""
        remote = self.repository_of(id)

        if remote is None:
            raise Conflict("this app has no remote repository")

        kind, repo = remote

        if credentials.kind and credentials.kind != kind:
            raise Conflict(
                f"the app lives on {kind}; the connected host is {credentials.kind}",
            )

        host = build_source_host(
            kind,
            repo,
            base_url=credentials.base_url,
            token=credentials.token,
            username=credentials.username,
        )

        if not isinstance(host, SupportsRepoDeletion):
            raise Conflict(f"{host.name} cannot delete repositories")

        try:
            host.delete_repository(repo)
        except ProviderError as e:
            raise Upstream(str(e)) from e

        return repo

    def delete_through_host(self, writes, organization_id: str, app) -> Optional[str]:
        """Delete the repository behind `app` with the host attached to it; None when the app has no remote."""
        try:
            remote = self.repository_of(app.registry_id)
        except ActionPlatformError:
            return None

        if remote is None:
            return None

        creds = writes.credentials_for(organization_id, app.source_host_id)

        if creds is None:
            raise Conflict(
                f"{app.name} lives on {remote[0]} but no connected host is attached to it; "
                "attach one in the app's settings or keep the repository",
            )

        return self.delete_repository(
            app.registry_id, SourceCredentials(**creds.as_dict())
        )
