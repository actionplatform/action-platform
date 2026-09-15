"""The repository behind an app on its code host."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from action_platform.api.schemas import SourceCredentials
from action_platform.api.services.shared.urls import GitUrl
from action_platform.api.services.workspace.manifest import AppManifest
from action_platform.core.exception import ProviderError
from action_platform.providers.source import build_source_host

from action_platform.api.services.apps.base import AppsBase


class AppRemote(AppsBase):
    def repository_of(self, id: str) -> Optional[tuple[str, str]]:
        """(kind, owner/name) of the remote this app was pushed to or added from; None when it has none."""
        entry, root = self.workspace(id)

        if not entry.url:
            return None

        try:
            host = AppManifest(root).as_dict()["source_host"]
        except HTTPException:
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
            raise HTTPException(409, "this app has no remote repository")

        kind, repo = remote

        if credentials.kind and credentials.kind != kind:
            raise HTTPException(
                409,
                f"the app lives on {kind}; the connected host is {credentials.kind}",
            )

        host = build_source_host(
            kind,
            repo,
            base_url=credentials.base_url,
            token=credentials.token,
            username=credentials.username,
        )

        try:
            host.delete_repository(repo)
        except NotImplementedError as e:
            raise HTTPException(409, str(e)) from e
        except ProviderError as e:
            raise HTTPException(502, str(e)) from e

        return repo
