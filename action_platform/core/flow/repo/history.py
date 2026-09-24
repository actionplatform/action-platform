"""The working tree and its commits: what changed, what was committed, recording new commits."""

from __future__ import annotations

from action_platform.core.flow.repo.runner import GitCommands, checked


NO_COMMITS = ("does not have any commits yet",)


class History(GitCommands):
    def is_clean(self) -> bool:
        return self.run(["status", "--porcelain"]) == ""

    def changed_files(self) -> list[str]:
        args = ["status", "--porcelain=v1", "--untracked-files=all", "-z"]
        out = checked(self.attempt(args), args).stdout

        return sorted({entry[3:] for entry in out.split("\0") if len(entry) > 3})

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
        out = self.lookup(
            ["log", "--diff-filter=A", "--format=%H", "--", relative],
            markers=NO_COMMITS,
        )
        lines = (out or "").splitlines()

        return lines[-1] if lines else None

    def add(self, paths: list[str]) -> None:
        self.run(["add", "--", *paths])

    def add_all(self) -> None:
        self.run(["add", "-A"])

    def commit(self, message: str) -> None:
        self.run(["commit", "-m", message, "--end-of-options"])
