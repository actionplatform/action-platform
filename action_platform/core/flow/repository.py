"""One git working copy: every command the platform runs against a clone, as methods on the clone."""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from action_platform.abc.vcs import Vcs
from action_platform.core.exception import ActionPlatformError
from action_platform.core.flow.git import check_ref, git_env


class SyncError(ActionPlatformError):
    """The clone could not be brought level with its remote."""


class Repository(Vcs):
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def __repr__(self) -> str:
        return f"Repository({str(self.path)!r})"

    def __fspath__(self) -> str:
        return str(self.path)

    @classmethod
    def init(cls, path: Path, branch: str = "main") -> "Repository":
        repo = cls(path)
        repo.run(["init", "-q", "-b", branch])

        return repo

    @classmethod
    def clone(
        cls,
        url: str,
        path: Path,
        depth: int | None = None,
        branch: str | None = None,
    ) -> "Repository":
        args = ["clone", "--quiet"]

        if depth:
            args += ["--depth", str(depth)]

        if branch:
            args += ["--branch", check_ref(branch)]

        args += ["--end-of-options", url, str(path)]
        subprocess.run(
            ["git", *args], check=True, capture_output=True, text=True, env=git_env()
        )

        return cls(path)

    def run(self, args: list[str]) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.path,
            check=True,
            capture_output=True,
            text=True,
            env=git_env(),
        )

        return result.stdout.strip()

    def attempt(self, args: list[str]) -> subprocess.CompletedProcess:
        """Run without raising; the caller reads returncode/stderr."""
        return subprocess.run(
            ["git", *args],
            cwd=self.path,
            capture_output=True,
            text=True,
            env=git_env(),
        )

    def exists(self) -> bool:
        return (self.path / ".git").exists()

    @property
    def branch(self) -> str:
        try:
            return self.run(["symbolic-ref", "--short", "-q", "HEAD"])
        except subprocess.CalledProcessError:
            return self.run(["rev-parse", "--abbrev-ref", "HEAD"])

    @property
    def head(self) -> str:
        return self.run(["rev-parse", "HEAD"])

    def short_head(self) -> str:
        return self.run(["rev-parse", "--short", "HEAD"])

    def is_clean(self) -> bool:
        return self.run(["status", "--porcelain"]) == ""

    def changed_files(self) -> list[str]:
        out = self.attempt(
            ["status", "--porcelain=v1", "--untracked-files=all", "-z"]
        ).stdout

        return sorted({entry[3:] for entry in out.split("\0") if len(entry) > 3})

    def remote_url(self, remote: str = "origin") -> str:
        try:
            return self.run(["remote", "get-url", remote])
        except subprocess.CalledProcessError:
            return ""

    def add_remote(self, url: str, remote: str = "origin") -> None:
        self.run(["remote", "add", remote, url])

    def tags(self) -> list[str]:
        return [t for t in self.run(["tag", "--list"]).split("\n") if t]

    def latest_tag(self, match: str | None = None) -> str | None:
        args = ["describe", "--tags", "--abbrev=0"]

        if match:
            args += ["--match", match]

        try:
            return self.run(args)
        except subprocess.CalledProcessError:
            return None

    def remote_tag_exists(self, tag: str, remote: str = "origin") -> bool:
        try:
            return bool(
                self.run(["ls-remote", "--tags", remote, f"refs/tags/{tag}"]).strip()
            )
        except subprocess.CalledProcessError:
            return False

    def commits_since(
        self, ref: str | None, paths: list[str] | None = None
    ) -> list[str]:
        args = ["log", f"{ref}..HEAD" if ref else "HEAD", "--pretty=format:%s"]

        if paths:
            args += ["--", *paths]

        return [line for line in self.run(args).split("\n") if line]

    def subjects(self, *revisions: str, ancestry_path: str | None = None) -> list[str]:
        args = ["log", *revisions, "--pretty=format:%s"]

        if ancestry_path:
            args.insert(1, f"--ancestry-path={ancestry_path}")

        return [line for line in self.run(args).split("\n") if line.strip()]

    def first_commit_adding(self, relative: str) -> str | None:
        try:
            out = self.run(["log", "--diff-filter=A", "--format=%H", "--", relative])
        except subprocess.CalledProcessError:
            return None

        lines = out.splitlines()

        return lines[-1] if lines else None

    def merge_base(self, a: str, b: str) -> str | None:
        try:
            return self.run(["merge-base", a, b])
        except subprocess.CalledProcessError:
            return None

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        return (
            self.attempt(
                ["merge-base", "--is-ancestor", ancestor, descendant]
            ).returncode
            == 0
        )

    def ref_exists(self, ref: str) -> bool:
        return (
            self.attempt(
                ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"]
            ).returncode
            == 0
        )

    def local_branch_exists(self, name: str) -> bool:
        return self.ref_exists(f"refs/heads/{name}")

    def tracking_branch_exists(self, name: str, remote: str = "origin") -> bool:
        return self.ref_exists(f"refs/remotes/{remote}/{name}")

    def remote_branch_exists(self, name: str, remote: str = "origin") -> bool:
        """Asked live; from the tracking refs of the last fetch when the remote cannot be reached without credentials."""
        try:
            return bool(
                self.run(["ls-remote", "--heads", remote, f"refs/heads/{name}"]).strip()
            )
        except subprocess.CalledProcessError:
            return self.tracking_branch_exists(name, remote)

    def upstream(self) -> str | None:
        result = self.attempt(
            ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"]
        )

        return result.stdout.strip() if result.returncode == 0 else None

    def tracks_a_remote(self) -> bool:
        branch = self.attempt(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()

        if not branch or branch == "HEAD":
            return False

        return (
            self.attempt(["config", "--get", f"branch.{branch}.remote"]).returncode == 0
        )

    def remote_head(self, remote: str = "origin") -> str | None:
        self.attempt(["remote", "set-head", remote, "--auto"])
        head = self.attempt(
            ["symbolic-ref", "--quiet", "--short", f"refs/remotes/{remote}/HEAD"]
        )

        if head.returncode != 0:
            return None

        name = head.stdout.strip().removeprefix(f"{remote}/")

        return name if self.tracking_branch_exists(name, remote) else None

    def default_branch(self, remote: str = "origin") -> str | None:
        head = self.attempt(["symbolic-ref", f"refs/remotes/{remote}/HEAD"])

        if head.returncode == 0:
            return head.stdout.strip().removeprefix(f"refs/remotes/{remote}/")

        for candidate in ("main", "master"):
            if self.remote_branch_exists(candidate, remote) or self.local_branch_exists(
                candidate
            ):
                return candidate

        return None

    def fetch(
        self, remote: str = "origin", prune: bool = True, tags: bool = True
    ) -> None:
        args = ["fetch", "--quiet"]

        if prune:
            args.append("--prune")

        if tags:
            args.append("--tags")

        self.run([*args, remote])

    def pull_ff(self) -> subprocess.CompletedProcess:
        return self.attempt(["pull", "--quiet", "--ff-only"])

    def reset_hard(self, ref: str = "HEAD") -> subprocess.CompletedProcess:
        return self.attempt(["reset", "--quiet", "--hard", ref])

    def clean(self) -> None:
        self.attempt(["clean", "-fdq"])

    @contextmanager
    def stashed(self) -> Iterator[None]:
        """Keep uncommitted work (untracked files included) across the block; when the pop conflicts, the stashed versions win."""
        stash = self.attempt(["stash", "push", "--quiet", "--include-untracked"])
        stashed = stash.returncode == 0 and "No local changes" not in stash.stdout

        try:
            yield
        finally:
            if stashed and self.attempt(["stash", "pop", "--quiet"]).returncode != 0:
                for tree in ("stash@{0}^3", "stash@{0}"):
                    self.attempt(["checkout", "--quiet", tree, "--", "."])

                self.attempt(["reset", "--quiet"])
                self.attempt(["stash", "drop", "--quiet"])

    def follow_remote(
        self, default_branch: str | None = None, reset: bool = False
    ) -> None:
        """Bring the clone level with its remote: fetch, fast-forward; uncommitted work survives the pull; a branch deleted on the remote (its pull request merged) is left for the default branch; a branch with commits the remote lacks is moved to the remote — the remote is the source of truth and such a commit is only ever a leftover from a failed push. `reset` drops everything local first."""
        try:
            self.fetch()
        except subprocess.CalledProcessError as e:
            raise SyncError(_fetch_problem(e.stderr or "")) from e

        if self.upstream() is None:
            if self.tracks_a_remote():
                self._leave_merged_branch(default_branch)

            return

        if reset:
            self.clean()
            pull = self.reset_hard("@{upstream}")
        else:
            pull = self.pull_ff()

        if pull.returncode != 0 and _blocked_by_local_changes(pull.stderr):
            with self.stashed():
                pull = self.pull_ff()

        if pull.returncode != 0 and _diverged(pull.stderr):
            with self.stashed():
                pull = self.reset_hard("@{upstream}")

        if pull.returncode != 0:
            raise SyncError(_pull_problem(pull.stderr))

    def _leave_merged_branch(self, default_branch: str | None) -> None:
        target = default_branch or "main"

        if not self.tracking_branch_exists(target):
            target = self.remote_head()

        if target is None:
            return

        with self.stashed():
            self.checkout_tracking(target)

    def checkout(
        self, branch: str, create: bool = False, start: str | None = None
    ) -> None:
        name = check_ref(branch)

        if create:
            self.run(["checkout", "-b", name, *([start] if start else [])])
        else:
            self.run(["checkout", "--end-of-options", name])

    def checkout_tracking(self, branch: str, remote: str = "origin") -> None:
        name = check_ref(branch)
        self.attempt(["checkout", "--quiet", "-B", name, f"{remote}/{name}"])

    def add(self, paths: list[str]) -> None:
        self.run(["add", "--", *paths])

    def add_all(self) -> None:
        self.run(["add", "-A"])

    def commit(self, message: str) -> None:
        self.run(["commit", "-m", message, "--end-of-options"])

    def tag(self, name: str, message: str | None = None) -> None:
        self.run(["tag", "-a", name, "-m", message or name])

    def delete_tag(self, name: str) -> None:
        self.run(["tag", "-d", name])

    def push(self, refspec: str = "HEAD", remote: str = "origin") -> None:
        self.run(["push", remote, refspec])

    def push_tag(self, tag: str, remote: str = "origin") -> None:
        self.run(["push", remote, tag])

    def push_upstream(self, branch: str, remote: str = "origin") -> None:
        self.run(["push", "-u", "--end-of-options", remote, check_ref(branch)])


def _diverged(stderr: str) -> bool:
    return "Not possible to fast-forward" in stderr or "diverged" in stderr


def _blocked_by_local_changes(stderr: str) -> bool:
    return "uncommitted changes" in stderr or "would be overwritten" in stderr


def _fetch_problem(stderr: str) -> str:
    text = stderr.strip()

    if (
        "could not read Username" in text
        or "Authentication failed" in text
        or "403" in text
    ):
        return "the code host refused the credentials — reconnect the source host in Settings"

    if "Could not resolve host" in text or "unable to access" in text:
        return "the code host could not be reached"

    if "not found" in text.lower() or "does not appear to be a git repository" in text:
        return "the repository no longer exists on the code host, or the account cannot see it"

    return text.splitlines()[-1] if text else "git fetch failed"


def _pull_problem(stderr: str) -> str:
    text = stderr.strip()

    if _diverged(text):
        return "could not move the branch to its remote"

    if _blocked_by_local_changes(text):
        return "working tree has changes that the remote would overwrite — commit them first"

    return text.splitlines()[-1] if text else "git pull failed"
