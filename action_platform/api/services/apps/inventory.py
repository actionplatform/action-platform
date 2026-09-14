"""Registering, listing, inspecting, refreshing and removing apps."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from action_platform.api.core import credentials as auth
from action_platform.api.repositories.registry import Entry, MissingManifest
from action_platform.api.schemas import InstallSpec, SourceCredentials
from action_platform.api.services.workspace.manifest import read_manifest
from action_platform.api.services.workspace import Workspaces
from action_platform.core.flow.repository import Repository
from action_platform.core.scaffold.install import InstallError, install
from action_platform.settings import settings

from action_platform.api.services.apps.base import AppsBase


class Inventory(AppsBase):
    def workspace(self, id: str) -> tuple[Entry, Path]:
        return Workspaces(self.registry).checkout(id)

    def list(self) -> list[dict]:
        """Every app with what the manifest says about it. Listing clones nothing: an app not checked out on this instance answers with its registry row only."""
        rows = []

        for entry in self.registry.list():
            root = Path(entry.path)
            row = asdict(entry)
            row["exists"] = bool(entry.url)
            row["branch"] = entry.checked_out

            if root.is_dir() and (root / settings.CONFIG_FILE).exists():
                info = read_manifest(root)
                row["language"] = info["project"].get("language")
                row["type"] = info["project"].get("type")
                row["last_version"] = info["last_version"]

            rows.append(row)

        return rows

    def add(
        self,
        url: str,
        name: Optional[str],
        credentials: Optional[SourceCredentials] = None,
        install_spec: Optional[InstallSpec] = None,
    ) -> dict:
        with auth.git_auth(credentials):
            try:
                entry = self.registry.add(
                    url, name, require_manifest=install_spec is None
                )
            except MissingManifest as e:
                raise HTTPException(
                    422, {"code": "needs_install", "detail": str(e)}
                ) from e

        result = asdict(entry)
        root = Path(entry.path)

        if install_spec is not None and not (root / settings.CONFIG_FILE).exists():
            try:
                plan = install(
                    root,
                    type_=install_spec.type,
                    language=install_spec.language,
                    ci=install_spec.ci,
                    name=entry.name,
                )
            except InstallError as e:
                self.registry.remove(entry.id)
                raise HTTPException(400, str(e)) from e

            result["installed"] = plan.created

            if self.registry.drafts is not None:
                self.registry.drafts.capture(entry.id, root)

        return result

    def sync(
        self,
        id: str,
        credentials: Optional[SourceCredentials] = None,
        reset: bool = False,
    ) -> dict:
        if reset:
            self.registry.drafts.clear(id)

        with auth.git_auth(credentials):
            entry, _ = Workspaces(self.registry).refresh(id)

        return asdict(entry)

    def remove(self, id: str) -> None:
        entry = self.registry.get(id)
        self.registry.remove(id)
        Workspaces(self.registry).drop(id, Path(entry.path))

    def detail(self, id: str) -> dict:
        entry, root = self.workspace(id)
        info = read_manifest(root)
        info["id"] = id
        info["url"] = entry.url
        info["default_branch"] = entry.default_branch

        repo = Repository(root)
        info["branch"] = repo.branch if repo.exists() else entry.checked_out
        info["latest_tag"] = repo.latest_tag() if repo.exists() else None
        info["clean"] = not self.registry.drafts.paths(id)

        return info
