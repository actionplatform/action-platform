"""Branches and refs: where HEAD is, which refs exist, how they relate, switching between them."""

from __future__ import annotations

from action_platform.core.flow.git import check_ref
from action_platform.core.flow.repo.runner import GitCommands


class Branches(GitCommands):
    @property
    def branch(self) -> str:
        return self.lookup(
            ["symbolic-ref", "--short", "-q", "HEAD"], codes=(1,)
        ) or self.run(["rev-parse", "--abbrev-ref", "HEAD"])

    @property
    def head(self) -> str:
        return self.run(["rev-parse", "HEAD"])

    def short_head(self) -> str:
        return self.run(["rev-parse", "--short", "HEAD"])

    def merge_base(self, a: str, b: str) -> str | None:
        """None when the two share no history or either one does not exist."""
        return self.lookup(
            ["merge-base", a, b], codes=(1,), markers=("Not a valid object name",)
        )

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

    def checkout(
        self, branch: str, create: bool = False, start: str | None = None
    ) -> None:
        name = check_ref(branch)

        if create:
            self.run(["checkout", "-b", name, *([check_ref(start)] if start else [])])
        else:
            self.run(["checkout", "--end-of-options", name])

    def checkout_tracking(self, branch: str, remote: str = "origin") -> None:
        name = check_ref(branch)
        self.attempt(["checkout", "--quiet", "-B", name, f"{remote}/{name}"])
