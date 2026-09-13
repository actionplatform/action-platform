"""Which apps (git repositories) the API manages.

Each entry is a git URL cloned into its own workspace under the API's home
(`~/.action-platform/workspaces/<id>`). The web app adds and removes
entries; ids are stable so links survive a rename. Nothing here points at
a directory the user did not ask the platform to own.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from ulid import ULID

from action_platform.core.exception import ActionPlatformError
from action_platform.core.flow.git import UnsafeUrl, check_remote_url, git_env
from action_platform.settings import settings


class SyncError(ActionPlatformError):
    pass


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
            subprocess.run(
                ["git", "clone", "--quiet", url, str(path)],
                check=True,
                capture_output=True,
                text=True,
                env=git_env(),
            )
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

        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=path,
            capture_output=True,
            env=git_env(),
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
            env=git_env(),
        )
        upstream = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
            cwd=root,
            capture_output=True,
            env=git_env(),
            text=True,
        )

        if upstream.returncode != 0:
            return entry

        pull = subprocess.run(
            ["git", "pull", "--quiet", "--ff-only"],
            cwd=root,
            capture_output=True,
            env=git_env(),
            text=True,
        )

        if pull.returncode != 0:
            raise SyncError(_pull_problem(pull.stderr))

        check_workspace(root)

        return entry

    def remove(self, id: str) -> None:
        entry = self.get(id)
        rows = [r for r in self._load() if r.id != id]
        self._save(rows)

        path = Path(entry.path)

        if not path.is_symlink() and path.resolve().is_relative_to(
            self.workspaces.resolve()
        ):
            shutil.rmtree(path, ignore_errors=True)


def _pull_problem(stderr: str) -> str:
    text = stderr.strip()

    if "Not possible to fast-forward" in text or "diverged" in text:
        return (
            "local branch diverged from its remote — rebase or reset it before syncing"
        )

    if "uncommitted changes" in text or "would be overwritten" in text:
        return "working tree has changes that the remote would overwrite — commit them first"

    return text.splitlines()[-1] if text else "git pull failed"


def _name_from(url: str) -> str:
    tail = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]

    return tail[:-4] if tail.endswith(".git") else tail
