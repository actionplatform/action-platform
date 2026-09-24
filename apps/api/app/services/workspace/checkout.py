"""A disposable clone per app: rebuilt from the remote when missing, brought level with it before every use, with the app's pending edits written on top.

Nothing survives here that is not on the remote or in the database, so any
API instance or worker can serve any app from an empty disk.
"""

import shutil
import subprocess
import threading
import time
from pathlib import Path


from action_platform.core.exception import ActionPlatformError
from action_platform.core.flow.git import UnsafeUrl, check_remote_url
from action_platform.core.flow.repository import Repository, SyncError, _fetch_problem
from action_platform.core.scaffold.installer import InstallError, install
from action_platform.settings import settings
from app.core.errors import Gone, Upstream
from app.repositories.workspace.registry import (
    Entry,
    MissingManifest,
    Registry,
    UnsafeWorkspace,
    check_workspace,
    name_from_url,
)


class Clones:
    """Per-process bookkeeping of the clones on disk: one lock per app, and when each was last leveled with its remote."""

    def __init__(self) -> None:
        self.locks: dict[str, threading.Lock] = {}
        self.guard = threading.Lock()
        self.fresh: dict[str, float] = {}

    def lock(self, id: str) -> threading.Lock:
        with self.guard:
            return self.locks.setdefault(id, threading.Lock())

    def leveled(self, id: str) -> None:
        self.fresh[id] = time.monotonic()

    def stale(self, id: str, ttl: float) -> bool:
        return time.monotonic() - self.fresh.get(id, 0) > ttl

    def forget(self, id: str) -> None:
        with self.guard:
            self.locks.pop(id, None)
            self.fresh.pop(id, None)


CLONES = Clones()


class Workspaces:
    def __init__(self, registry: Registry, ttl: float | None = None) -> None:
        self.registry = registry
        self.ttl = settings.workspaces.ttl if ttl is None else ttl
        self.clones = CLONES

    def adopt(
        self, url: str, name: str | None = None, require_manifest: bool = True
    ) -> Entry:
        """Bring a repository in: validate the url, clone it into a workspace, check the clone, register the entry. An already registered url answers its entry."""
        url = url.strip()

        if not url or any(c.isspace() for c in url):
            raise ActionPlatformError(f"not a git url: {url}")

        try:
            check_remote_url(url)
        except UnsafeUrl as e:
            raise ActionPlatformError(str(e)) from e

        known = self.registry.by_url(url)

        if known is not None:
            return known

        id = self.registry.new_id()
        path = self.registry.workspaces / id
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

        return self.registry.register(
            Entry(
                id=id,
                name=name or name_from_url(url),
                url=url,
                path=str(path),
                default_branch=repo.branch,
            )
        )

    def checkout(self, id: str, fresh: bool = False) -> tuple[Entry, Path]:
        """The app's clone on the branch it is checked out on, level with the remote, drafts applied."""
        entry = self.registry.get(id)
        root = Path(entry.path)

        with self.clones.lock(id):
            if not root.is_dir():
                self._clone(entry, root)
                self.clones.forget(id)

            repo = Repository(root)
            leveled = fresh or self.clones.stale(id, self.ttl)

            if leveled:
                self._level(repo, entry)
                self.clones.leveled(id)

            installed = self.ensure_platform(entry, root)

            if self.registry.drafts is not None:
                drafted = self.registry.drafts.overlay(id, root)

                if installed or (leveled and drafted):
                    self.registry.drafts.capture(id, root)

        return entry, root

    def refresh(self, id: str) -> tuple[Entry, Path]:
        return self.checkout(id, fresh=True)

    def drop(self, id: str, root: Path) -> None:
        self.clones.forget(id)

        if not root.is_symlink() and root.resolve().is_relative_to(
            self.registry.workspaces.resolve()
        ):
            shutil.rmtree(root, ignore_errors=True)

    def _clone(self, entry: Entry, root: Path) -> None:
        if not entry.url:
            raise Gone(f"{entry.name} has no remote to clone from")

        root.parent.mkdir(parents=True, exist_ok=True)

        try:
            Repository.clone(entry.url, root)
        except subprocess.CalledProcessError as e:
            shutil.rmtree(root, ignore_errors=True)

            raise Upstream(
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
            fallback = self.remote_default(repo, entry.default_branch)

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

    @staticmethod
    def remote_default(repo: Repository, known: str) -> str:
        """The branch the remote points HEAD at, else the first of the known default, main and master that exists there."""
        repo.attempt(["remote", "set-head", "origin", "--auto"])
        head = repo.attempt(
            ["symbolic-ref", "-q", "refs/remotes/origin/HEAD"]
        ).stdout.strip()
        pointed = (
            head.removeprefix("refs/remotes/origin/")
            if head.startswith("refs/remotes/origin/")
            else ""
        )

        for candidate in (pointed, known, "main", "master"):
            if candidate and repo.tracking_branch_exists(candidate):
                return candidate

        return ""

    @staticmethod
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
