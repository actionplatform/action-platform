"""A disposable clone per app: rebuilt from the remote when missing, brought level with it before every use, with the app's pending edits written on top.

Nothing survives here that is not on the remote or in the database, so any
API instance or worker can serve any app from an empty disk.
"""

import shutil
import subprocess
import threading
import time
from pathlib import Path

from fastapi import HTTPException

from action_platform.api.repositories.registry import (
    Entry,
    Registry,
    UnsafeWorkspace,
    check_workspace,
)
from action_platform.core.exception import ActionPlatformError
from action_platform.core.flow.repository import Repository, SyncError, _fetch_problem
from action_platform.core.scaffold.install import InstallError, install
from action_platform.settings import settings

LOCKS: dict[str, threading.Lock] = {}
LOCKS_GUARD = threading.Lock()
FRESH: dict[str, float] = {}


def lock_for(id: str) -> threading.Lock:
    with LOCKS_GUARD:
        return LOCKS.setdefault(id, threading.Lock())


def forget(id: str) -> None:
    with LOCKS_GUARD:
        LOCKS.pop(id, None)
        FRESH.pop(id, None)


class Workspaces:
    def __init__(self, registry: Registry, ttl: float | None = None) -> None:
        self.registry = registry
        self.ttl = settings.WORKSPACE_TTL if ttl is None else ttl

    def checkout(self, id: str, fresh: bool = False) -> tuple[Entry, Path]:
        """The app's clone on the branch it is checked out on, level with the remote, drafts applied."""
        entry = self.registry.get(id)
        root = Path(entry.path)

        with lock_for(id):
            if not root.is_dir():
                self._clone(entry, root)
                FRESH.pop(id, None)

            repo = Repository(root)
            leveled = fresh or time.monotonic() - FRESH.get(id, 0) > self.ttl

            if leveled:
                self._level(repo, entry)
                FRESH[id] = time.monotonic()

            installed = ensure_platform(entry, root)

            if self.registry.drafts is not None:
                drafted = self.registry.drafts.overlay(id, root)

                if installed or (leveled and drafted):
                    self.registry.drafts.capture(id, root)

        return entry, root

    def refresh(self, id: str) -> tuple[Entry, Path]:
        return self.checkout(id, fresh=True)

    def drop(self, id: str, root: Path) -> None:
        forget(id)

        if not root.is_symlink() and root.resolve().is_relative_to(
            self.registry.workspaces.resolve()
        ):
            shutil.rmtree(root, ignore_errors=True)

    def _clone(self, entry: Entry, root: Path) -> None:
        if not entry.url:
            raise HTTPException(410, f"{entry.name} has no remote to clone from")

        root.parent.mkdir(parents=True, exist_ok=True)

        try:
            Repository.clone(entry.url, root)
        except subprocess.CalledProcessError as e:
            shutil.rmtree(root, ignore_errors=True)

            raise HTTPException(
                502,
                f"clone of {entry.name} failed: {(e.stderr or '').strip() or entry.url}",
            ) from e

        try:
            check_workspace(root)
        except UnsafeWorkspace:
            shutil.rmtree(root, ignore_errors=True)
            raise

    def _level(self, repo: Repository, entry: Entry) -> None:
        """Discard whatever the clone has and match the remote branch the app is on; the draft is the only local state, and it is written back afterwards."""
        branch = entry.checked_out

        try:
            repo.fetch()
        except subprocess.CalledProcessError as e:
            raise SyncError(_fetch_problem(e.stderr or "")) from e

        repo.reset_hard()
        repo.clean()

        if not repo.tracking_branch_exists(branch):
            fallback = remote_default(repo, entry.default_branch)

            if fallback and fallback != branch:
                entry.default_branch = fallback
                entry.branch = ""
                self.registry.register(entry)
                branch = fallback

        if repo.tracking_branch_exists(branch):
            repo.run(["checkout", "-q", "-B", branch, f"origin/{branch}"])
            repo.run(["branch", "-q", f"--set-upstream-to=origin/{branch}", branch])
        elif repo.local_branch_exists(branch):
            repo.run(["checkout", "-q", branch])
        else:
            raise SyncError(
                f"branch {branch} no longer exists on the remote of {entry.name}"
            )

        check_workspace(Path(repo.path))


def remote_default(repo: Repository, known: str) -> str:
    """The branch the remote points HEAD at, else the first of the known default, main and master that exists there."""
    head = repo.attempt(
        ["symbolic-ref", "-q", "refs/remotes/origin/HEAD"]
    ).stdout.strip()

    if head.startswith("refs/remotes/origin/"):
        return head.removeprefix("refs/remotes/origin/")

    for candidate in (known, "main", "master"):
        if candidate and repo.tracking_branch_exists(candidate):
            return candidate

    return ""


def ensure_platform(entry: Entry, root: Path) -> list[str]:
    """A clone that lost `platform.toml` (a branch from before the platform) gets the platform files back, uncommitted, so the app never shows an error for something the platform can fix itself."""
    if (root / settings.CONFIG_FILE).exists() or not (root / ".git").exists():
        return []

    ci = (
        "gitlab"
        if "gitlab" in entry.url
        else "bitbucket"
        if "bitbucket" in entry.url
        else "github"
    )

    try:
        plan = install(root, type_="web", ci=ci, name=entry.name)
    except InstallError:
        plan = install(root, type_="web", language="none", ci=ci, name=entry.name)

    return plan.created


def workspace_of(registry: Registry, id: str) -> tuple[Entry, Path]:
    try:
        return Workspaces(registry).checkout(id)
    except ActionPlatformError as e:
        raise HTTPException(410, str(e)) from e
