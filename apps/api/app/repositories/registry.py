"""Which apps (git repositories) the API manages.

Each entry is a git URL plus the branch the app is checked out on. The clone
itself is disposable: it lives under a temporary directory
(`AP_WORKSPACES`, default the system temp dir) and is rebuilt from the URL
and brought level with the remote whenever a request needs it — no instance
or worker keeps state on disk. Edits not committed yet live in the `draft`
table, not in the clone.

Entries live in the database (`registry` table), so every instance and
worker sees the same apps. An `apps.json` under the home from older
versions is imported once.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from ulid import ULID

from app.core.db.models import RegistryEntry

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
    branch: str = ""

    @property
    def checked_out(self) -> str:
        return self.branch or self.default_branch or "main"


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
                    "branch": r.branch,
                }
                for r in s.scalars(
                    select(RegistryEntry).order_by(RegistryEntry.created_at)
                )
            ]

    def row(self, id: str) -> Optional[dict]:
        with self.database.session() as s:
            r = s.get(RegistryEntry, id)

            if r is None:
                return None

            return {
                "id": r.id,
                "name": r.name,
                "url": r.url,
                "default_branch": r.default_branch,
                "branch": r.branch,
            }

    def put(self, row: dict) -> None:
        with self.database.session() as s:
            entry = s.get(RegistryEntry, row["id"]) or RegistryEntry(id=row["id"])
            entry.name = row["name"]
            entry.url = row["url"]
            entry.default_branch = row.get("default_branch", "")
            entry.branch = row.get("branch", "")
            s.add(entry)

    def delete(self, id: str) -> None:
        with self.database.session() as s:
            entry = s.get(RegistryEntry, id)

            if entry is not None:
                s.delete(entry)


class Registry:
    def __init__(
        self, store: DbStore, drafts=None, root: Optional[Path] = None
    ) -> None:
        self.root = root or home()
        self.file = self.root / "apps.json"
        self.workspaces = settings.WORKSPACES
        self.store = store
        self.drafts = drafts

    def _entry(self, row: dict) -> Entry:
        return Entry(
            id=row["id"],
            name=row["name"],
            url=row.get("url", ""),
            path=str(self.workspaces / row["id"]),
            default_branch=row.get("default_branch", ""),
            branch=row.get("branch", ""),
        )

    def _load(self) -> list[Entry]:
        return [self._entry(row) for row in self.store.rows()]

    def _put(self, entry: Entry) -> None:
        row = asdict(entry)
        row.pop("path")
        self.store.put(row)

    def adopt_file(self) -> list[str]:
        """An `apps.json` from before the registry lived in the database is imported once, ids kept, then renamed so it is never read again."""
        if not self.file.exists():
            return []

        known = {row["id"] for row in self.store.rows()}
        adopted = []

        for row in json.loads(self.file.read_text() or "[]"):
            if row["id"] in known:
                continue

            self.store.put({k: v for k, v in row.items() if k != "path"})
            adopted.append(row["id"])

        self.file.rename(self.file.with_suffix(".json.imported"))

        return adopted

    def list(self) -> list[Entry]:
        return self._load()

    def get(self, id: str) -> Entry:
        row = self.store.row(id)

        if row is None:
            raise ActionPlatformError(f"app {id} is not registered")

        return self._entry(row)

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
        """Record an app the platform generated and pushed itself."""
        self._put(entry)

        return entry

    def set_branch(self, id: str, branch: str) -> Entry:
        entry = self.get(id)
        entry.branch = "" if branch == entry.default_branch else branch
        self._put(entry)

        return entry

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
