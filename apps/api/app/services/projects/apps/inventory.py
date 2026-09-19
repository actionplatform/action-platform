"""Registering, listing, inspecting, refreshing and removing apps."""

from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Optional


from action_platform.core.scaffold.install import InstallError, install
from action_platform.settings import settings
from app.services.workspace import git_auth as auth
from app.repositories.workspace.registry import Entry, MissingManifest
from app.repositories.workspace.snapshots import SnapshotStore
from app.schemas import InstallSpec, SourceCredentials
from app.services.projects.apps.base import AppsBase
from app.services.workspace.checkout import Workspaces
from app.services.workspace.facts import AppFacts
from app.services.workspace.snapshot import SnapshotService
from app.services.workspace.manifest import AppManifest
from app.core.errors import Invalid, NeedsInstall

log = logging.getLogger(__name__)


class AppInventory(AppsBase):
    def workspace(self, id: str) -> tuple[Entry, Path]:
        return Workspaces(self.registry).checkout(id)

    def list(self, only: set[str] | None = None) -> list[dict]:
        """Every app — or the ones in `only` — with what the platform knows about it: the snapshot taken after the last change, the clone when this instance has one and no snapshot exists yet. Listing clones nothing."""
        snapshots = SnapshotStore(self.registry.store.database)
        rows = []

        for entry in self.registry.list():
            if only is not None and entry.id not in only:
                continue

            row = asdict(entry)
            row["exists"] = bool(entry.url)
            row["branch"] = entry.checked_out
            row.update(self._summary(entry, snapshots.get(entry.id)))
            rows.append(row)

        return rows

    def _summary(self, entry: Entry, snapshot: Optional[tuple[dict, object]]) -> dict:
        if snapshot is not None:
            detail = snapshot[0].get("detail") or {}
            project = detail.get("project") or {}

            deploy = detail.get("deploy") or {}

            return {
                "language": project.get("language"),
                "type": project.get("type"),
                "last_version": detail.get("last_version"),
                "branch": detail.get("branch") or entry.checked_out,
                "deploy_target": deploy.get("target")
                if isinstance(deploy.get("target"), str)
                else None,
            }

        root = Path(entry.path)

        if not (root.is_dir() and (root / settings.CONFIG_FILE).exists()):
            return {}

        info = AppManifest(root, self.configs.resolve(entry.id, root)).as_dict()

        deploy = info.get("deploy") or {}

        return {
            "language": info["project"].get("language"),
            "type": info["project"].get("type"),
            "last_version": info["last_version"],
            "deploy_target": deploy.get("target")
            if isinstance(deploy.get("target"), str)
            else None,
        }

    def add(
        self,
        url: str,
        name: Optional[str],
        credentials: Optional[SourceCredentials] = None,
        install_spec: Optional[InstallSpec] = None,
    ) -> dict:
        with auth.git_auth(credentials):
            try:
                entry = Workspaces(self.registry).adopt(
                    url, name, require_manifest=install_spec is None
                )
            except MissingManifest as e:
                raise NeedsInstall(str(e)) from e

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
                raise Invalid(str(e)) from e

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

        self._snapshot(id)

        return asdict(entry)

    def _snapshot(self, id: str) -> None:
        try:
            SnapshotService(self.registry, self.configs).take(id)
        except Exception:
            log.warning("snapshot of %s failed", id, exc_info=True)

    def remove(self, id: str) -> None:
        entry = self.registry.get(id)
        SnapshotService(self.registry, self.configs).forget(id)
        self.registry.remove(id)
        Workspaces(self.registry).drop(id, Path(entry.path))

    def detail(self, id: str) -> dict:
        return AppFacts(self.registry, self.configs).detail(id)
