"""Remotes: their urls and branches, the upstream of HEAD, fetching and pushing."""

from __future__ import annotations

import subprocess

from action_platform.core.flow.git import check_ref
from action_platform.core.flow.repo.branches import Branches


NO_UPSTREAM = (
    "no upstream configured",
    "HEAD does not point to a branch",
    "no such branch",
)


class Remotes(Branches):
    def remote_url(self, remote: str = "origin") -> str:
        return self.lookup(["remote", "get-url", remote], codes=(2,)) or ""

    def add_remote(self, url: str, remote: str = "origin") -> None:
        self.run(["remote", "add", remote, url])

    def remote_tag_exists(self, tag: str, remote: str = "origin") -> bool:
        """False when there is no such remote; a remote that cannot be asked raises."""
        if not self.remote_url(remote):
            return False

        return bool(self.run(["ls-remote", "--tags", remote, f"refs/tags/{tag}"]))

    def remote_branch_exists(self, name: str, remote: str = "origin") -> bool:
        """Asked live; from the tracking refs of the last fetch when the remote cannot be reached without credentials."""
        try:
            return bool(
                self.run(["ls-remote", "--heads", remote, f"refs/heads/{name}"]).strip()
            )
        except subprocess.CalledProcessError:
            return self.tracking_branch_exists(name, remote)

    def upstream(self) -> str | None:
        return self.lookup(
            ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
            markers=NO_UPSTREAM,
        )

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

    def push(self, refspec: str = "HEAD", remote: str = "origin") -> None:
        self.run(["push", remote, refspec])

    def push_tag(self, tag: str, remote: str = "origin") -> None:
        self.run(["push", remote, tag])

    def push_upstream(self, branch: str, remote: str = "origin") -> None:
        self.run(["push", "-u", "--end-of-options", remote, check_ref(branch)])
