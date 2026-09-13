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

    def sync(self, id: str, reset: bool = False) -> Entry:
        """fetch + fast-forward the workspace to its remote. No-op without a remote. `reset` drops local commits and changes so the branch matches the remote."""
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
            if _tracks_a_remote(root):
                _leave_merged_branch(root, entry.default_branch)
                check_workspace(root)

            return entry

        if reset:
            subprocess.run(
                ["git", "clean", "-fdq"], cwd=root, capture_output=True, env=git_env()
            )
            pull = _reset_to_upstream(root)
        else:
            pull = _pull(root)

        if pull.returncode != 0 and _blocked_by_local_changes(pull.stderr):
            pull = _pull_over_local_changes(root)

        if (
            pull.returncode != 0
            and _diverged(pull.stderr)
            and _nothing_only_local(root)
        ):
            pull = _reset_to_upstream(root)

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


def _pull(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "pull", "--quiet", "--ff-only"],
        cwd=root,
        capture_output=True,
        env=git_env(),
        text=True,
    )


def _ref_exists(root: Path, ref: str) -> bool:
    return (
        subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
            cwd=root,
            capture_output=True,
            env=git_env(),
        ).returncode
        == 0
    )


def _tracks_a_remote(root: Path) -> bool:
    """The branch is configured to follow a remote branch that no longer exists (deleted after its pull request merged)."""
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=root,
        capture_output=True,
        env=git_env(),
        text=True,
    ).stdout.strip()

    if not branch or branch == "HEAD":
        return False

    return (
        subprocess.run(
            ["git", "config", "--get", f"branch.{branch}.remote"],
            cwd=root,
            capture_output=True,
            env=git_env(),
        ).returncode
        == 0
    )


def _leave_merged_branch(root: Path, default_branch: str) -> None:
    """The branch was deleted on the remote (merged pull request): go back to the default branch and bring it up to date."""
    target = default_branch or "main"

    if not _ref_exists(root, f"origin/{target}"):
        target = _remote_head(root)

    if target is None:
        return

    subprocess.run(
        ["git", "stash", "push", "--quiet", "--include-untracked"],
        cwd=root,
        capture_output=True,
        env=git_env(),
    )
    subprocess.run(
        ["git", "checkout", "--quiet", "-B", target, f"origin/{target}"],
        cwd=root,
        capture_output=True,
        env=git_env(),
    )
    subprocess.run(
        ["git", "stash", "pop", "--quiet"],
        cwd=root,
        capture_output=True,
        env=git_env(),
    )


def _remote_head(root: Path) -> str | None:
    subprocess.run(
        ["git", "remote", "set-head", "origin", "--auto"],
        cwd=root,
        capture_output=True,
        env=git_env(),
    )
    head = subprocess.run(
        ["git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
        cwd=root,
        capture_output=True,
        env=git_env(),
        text=True,
    )

    if head.returncode != 0:
        return None

    name = head.stdout.strip().removeprefix("origin/")

    return name if _ref_exists(root, f"origin/{name}") else None


def _diverged(stderr: str) -> bool:
    return "Not possible to fast-forward" in stderr or "diverged" in stderr


def _nothing_only_local(root: Path) -> bool:
    """True when every local commit is already upstream (same patch), so the local branch can follow the remote."""
    cherry = subprocess.run(
        ["git", "cherry", "@{upstream}"],
        cwd=root,
        capture_output=True,
        env=git_env(),
        text=True,
    )

    if cherry.returncode != 0:
        return False

    return not any(line.startswith("+") for line in cherry.stdout.splitlines())


def _reset_to_upstream(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "reset", "--quiet", "--hard", "@{upstream}"],
        cwd=root,
        capture_output=True,
        env=git_env(),
        text=True,
    )


def _blocked_by_local_changes(stderr: str) -> bool:
    return "uncommitted changes" in stderr or "would be overwritten" in stderr


def _pull_over_local_changes(root: Path) -> subprocess.CompletedProcess:
    stash = subprocess.run(
        ["git", "stash", "push", "--quiet", "--include-untracked"],
        cwd=root,
        capture_output=True,
        env=git_env(),
        text=True,
    )

    if stash.returncode != 0:
        return stash

    pull = _pull(root)
    pop = subprocess.run(
        ["git", "stash", "pop", "--quiet"],
        cwd=root,
        capture_output=True,
        env=git_env(),
        text=True,
    )

    if pop.returncode != 0:
        for tree in ("stash@{0}^3", "stash@{0}"):
            subprocess.run(
                ["git", "checkout", "--quiet", tree, "--", "."],
                cwd=root,
                capture_output=True,
                env=git_env(),
            )

        subprocess.run(
            ["git", "reset", "--quiet"], cwd=root, capture_output=True, env=git_env()
        )
        subprocess.run(
            ["git", "stash", "drop", "--quiet"],
            cwd=root,
            capture_output=True,
            env=git_env(),
        )

    return pull


def _pull_problem(stderr: str) -> str:
    text = stderr.strip()

    if _diverged(text):
        return "local branch has commits the remote does not — push them, or reset the branch, before syncing"

    if "uncommitted changes" in text or "would be overwritten" in text:
        return "working tree has changes that the remote would overwrite — commit them first"

    return text.splitlines()[-1] if text else "git pull failed"


def _name_from(url: str) -> str:
    tail = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]

    return tail[:-4] if tail.endswith(".git") else tail
