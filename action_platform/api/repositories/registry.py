"""Which apps (git repositories) the API manages.

Each entry is a git URL cloned into its own workspace under the API's home
(`~/.action-platform/workspaces/<id>`). The web app adds and removes
entries; ids are stable so links survive a rename. Nothing here points at
a directory the user did not ask the platform to own.

Entries live in the database (`registry` table) when the API has one, so
every instance and worker sees the same apps and rebuilds a missing
workspace from the URL; `apps.json` under the home is the file fallback.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional, Protocol

from sqlalchemy import select
from ulid import ULID

from action_platform.api.db.models import RegistryEntry

from action_platform.core.exception import ActionPlatformError
from action_platform.core.flow.repository import Repository
from action_platform.core.flow.git import UnsafeUrl, check_remote_url
from action_platform.settings import settings


class MissingManifest(ActionPlatformError):
    pass


class UnsafeWorkspace(ActionPlatformError):
    pass


def escaping_symlinks(root: Path) -> list[str]:
    """Symlinks under `root` (outside .git) whose target resolves outside `root`."""
    base = root.resolve()
    found: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        if ".git" in dirnames:
            dirnames.remove(".git")

        for name in dirnames + filenames:
            candidate = Path(dirpath) / name

            if not candidate.is_symlink():
                continue

            target = candidate.resolve()

            if not target.is_relative_to(base):
                found.append(str(candidate.relative_to(root)))

    return found


def check_workspace(root: Path) -> None:
    links = escaping_symlinks(root)

    if links:
        raise UnsafeWorkspace(
            "repository contains symlinks that point outside its tree: "
            + ", ".join(links[:5])
        )


def home() -> Path:
    base = os.environ.get("AP_HOME") or os.environ.get("XDG_CONFIG_HOME")

    return Path(base) / "action-platform" if base else Path.home() / ".action-platform"


@dataclass
class Entry:
    id: str
    name: str
    url: str
    path: str
    default_branch: str = ""


class Store(Protocol):
    def rows(self) -> list[dict]: ...

    def put(self, row: dict) -> None: ...

    def delete(self, id: str) -> None: ...


class FileStore:
    def __init__(self, file: Path) -> None:
        self.file = file

    def rows(self) -> list[dict]:
        if not self.file.exists():
            return []

        return json.loads(self.file.read_text() or "[]")

    def _write(self, rows: list[dict]) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(rows, indent=2) + "\n")

    def put(self, row: dict) -> None:
        self._write([r for r in self.rows() if r["id"] != row["id"]] + [row])

    def delete(self, id: str) -> None:
        self._write([r for r in self.rows() if r["id"] != id])


class DbStore:
    def __init__(self, database) -> None:
        self.database = database

    def rows(self) -> list[dict]:
        with self.database.session() as s:
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "url": r.url,
                    "default_branch": r.default_branch,
                }
                for r in s.scalars(
                    select(RegistryEntry).order_by(RegistryEntry.created_at)
                )
            ]

    def put(self, row: dict) -> None:
        with self.database.session() as s:
            entry = s.get(RegistryEntry, row["id"]) or RegistryEntry(id=row["id"])
            entry.name = row["name"]
            entry.url = row["url"]
            entry.default_branch = row.get("default_branch", "")
            s.add(entry)

    def delete(self, id: str) -> None:
        with self.database.session() as s:
            entry = s.get(RegistryEntry, id)

            if entry is not None:
                s.delete(entry)


class Registry:
    def __init__(
        self, root: Optional[Path] = None, store: Optional[Store] = None
    ) -> None:
        self.root = root or home()
        self.file = self.root / "apps.json"
        self.workspaces = self.root / "workspaces"
        self.store: Store = store or FileStore(self.file)

    def _entry(self, row: dict) -> Entry:
        return Entry(
            id=row["id"],
            name=row["name"],
            url=row.get("url", ""),
            path=row.get("path") or str(self.workspaces / row["id"]),
            default_branch=row.get("default_branch", ""),
        )

    def _load(self) -> list[Entry]:
        return [self._entry(row) for row in self.store.rows()]

    def _put(self, entry: Entry) -> None:
        row = asdict(entry)

        if isinstance(self.store, DbStore):
            row.pop("path")

        self.store.put(row)

    def list(self) -> list[Entry]:
        return self._load()

    def get(self, id: str) -> Entry:
        for row in self._load():
            if row.id == id:
                return row

        raise ActionPlatformError(f"app {id} is not registered")

    def add(
        self, url: str, name: Optional[str] = None, require_manifest: bool = True
    ) -> Entry:
        url = url.strip()

        if not url.strip() or any(c.isspace() for c in url):
            raise ActionPlatformError(f"not a git url: {url}")

        try:
            check_remote_url(url)
        except UnsafeUrl as e:
            raise ActionPlatformError(str(e)) from e

        rows = self._load()

        for row in rows:
            if row.url == url:
                return row

        id = str(ULID()).lower()
        name = name or _name_from(url)
        path = self.workspaces / id
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            repo = Repository.clone(url, path)
        except subprocess.CalledProcessError as e:
            raise ActionPlatformError(
                f"clone failed: {(e.stderr or '').strip() or url}"
            ) from e

        try:
            check_workspace(path)
        except UnsafeWorkspace:
            shutil.rmtree(path, ignore_errors=True)
            raise

        if require_manifest and not (path / settings.CONFIG_FILE).exists():
            shutil.rmtree(path, ignore_errors=True)

            raise MissingManifest(
                f"{settings.CONFIG_FILE} not found in {url} — install the platform on it first"
            )

        entry = Entry(
            id=id, name=name, url=url, path=str(path), default_branch=repo.branch
        )
        self._put(entry)

        return entry

    def new_id(self) -> str:
        return str(ULID()).lower()

    def register(self, entry: Entry) -> Entry:
        """Record a workspace the platform generated itself (url is empty until pushed)."""
        self._put(entry)

        return entry

    def sync(self, id: str, reset: bool = False) -> Entry:
        """fetch + fast-forward the workspace to its remote. No-op without a remote. `reset` drops local commits and changes so the branch matches the remote."""
        entry = self.get(id)

        if not entry.url:
            return entry

        root = Path(entry.path)
        self.restore(entry)
        Repository(root).follow_remote(entry.default_branch, reset=reset)
        check_workspace(root)

        return entry

    def restore(self, entry: Entry) -> bool:
        """Clone the workspace again when this instance does not have it; True when a clone happened."""
        root = Path(entry.path)

        if root.is_dir() or not entry.url:
            return False

        root.parent.mkdir(parents=True, exist_ok=True)

        try:
            Repository.clone(entry.url, root)
        except subprocess.CalledProcessError as e:
            shutil.rmtree(root, ignore_errors=True)

            raise ActionPlatformError(
                f"clone failed: {(e.stderr or '').strip() or entry.url}"
            ) from e

        try:
            check_workspace(root)
        except UnsafeWorkspace:
            shutil.rmtree(root, ignore_errors=True)
            raise

        return True

    def remove(self, id: str) -> None:
        entry = self.get(id)
        self.store.delete(id)

        path = Path(entry.path)

        if not path.is_symlink() and path.resolve().is_relative_to(
            self.workspaces.resolve()
        ):
            shutil.rmtree(path, ignore_errors=True)


def _name_from(url: str) -> str:
    tail = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]

    return tail[:-4] if tail.endswith(".git") else tail
