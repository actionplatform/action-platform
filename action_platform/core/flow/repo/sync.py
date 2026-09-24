"""Bringing a clone level with its remote: fast-forward, hard reset, stashing local work around both."""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from contextlib import contextmanager

from action_platform.core.exception import ActionPlatformError
from action_platform.core.flow.repo.remotes import Remotes


class SyncError(ActionPlatformError):
    """The clone could not be brought level with its remote."""


class Sync(Remotes):
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
