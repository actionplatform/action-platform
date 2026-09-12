"""Which apps (git repositories) the API manages.

Each entry is a git URL cloned into its own workspace under the API's home
(`~/.action-platform/workspaces/<id>`). The web app adds and removes
entries; ids are stable so links survive a rename. Nothing here points at
a directory the user did not ask the platform to own.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from ulid import ULID

from action_platform.core.exception import ActionPlatformError
from action_platform.settings import settings

URL_RE = re.compile(r"^(https?://|git@|ssh://|file://)[^\s]+$")


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


class Registry:
    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or home()
        self.file = self.root / "apps.json"
        self.workspaces = self.root / "workspaces"

    def _load(self) -> list[Entry]:
        if not self.file.exists():
            return []

        return [Entry(**row) for row in json.loads(self.file.read_text() or "[]")]

    def _save(self, rows: list[Entry]) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps([asdict(r) for r in rows], indent=2) + "\n")

    def list(self) -> list[Entry]:
        return self._load()

    def get(self, id: str) -> Entry:
        for row in self._load():
            if row.id == id:
                return row

        raise ActionPlatformError(f"app {id} is not registered")

    def add(self, url: str, name: Optional[str] = None) -> Entry:
        url = url.strip()

        if not URL_RE.match(url):
            raise ActionPlatformError(f"not a git url: {url}")

        rows = self._load()

        for row in rows:
            if row.url == url:
                return row

        id = str(ULID()).lower()
        name = name or _name_from(url)
        path = self.workspaces / id
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            subprocess.run(
                ["git", "clone", "--quiet", url, str(path)],
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            )
        except subprocess.CalledProcessError as e:
            raise ActionPlatformError(
                f"clone failed: {(e.stderr or '').strip() or url}"
            ) from e

        if not (path / settings.CONFIG_FILE).exists():
            shutil.rmtree(path, ignore_errors=True)
            raise ActionPlatformError(
                f"{settings.CONFIG_FILE} not found in {url} — run `action-platform install` there first"
            )

        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=path,
            capture_output=True,
            text=True,
        ).stdout.strip()

        entry = Entry(id=id, name=name, url=url, path=str(path), default_branch=branch)
        rows.append(entry)
        self._save(rows)

        return entry

    def new_id(self) -> str:
        return str(ULID()).lower()

    def register(self, entry: Entry) -> Entry:
        """Record a workspace the platform generated itself (url is empty until pushed)."""
        rows = [r for r in self._load() if r.id != entry.id]
        rows.append(entry)
        self._save(rows)

        return entry

    def sync(self, id: str) -> Entry:
        """fetch + fast-forward the workspace to its remote. No-op without a remote."""
        entry = self.get(id)

        if not entry.url:
            return entry

        root = Path(entry.path)

        subprocess.run(
            ["git", "fetch", "--quiet", "--prune", "--tags", "origin"],
            cwd=root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "pull", "--quiet", "--ff-only"],
            cwd=root,
            check=True,
            capture_output=True,
        )

        return entry

    def remove(self, id: str) -> None:
        entry = self.get(id)
        rows = [r for r in self._load() if r.id != id]
        self._save(rows)

        path = Path(entry.path)

        if path.is_relative_to(self.workspaces):
            shutil.rmtree(path, ignore_errors=True)


def _name_from(url: str) -> str:
    tail = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]

    return tail[:-4] if tail.endswith(".git") else tail
