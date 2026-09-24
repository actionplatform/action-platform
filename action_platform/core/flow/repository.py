"""One git working copy: every command the platform runs against a clone, as methods on the clone. The commands live in `core/flow/repo/`, one module per concern."""

from __future__ import annotations

from pathlib import Path

from action_platform.abc.working_copy import WorkingCopy
from action_platform.core.flow.git import check_ref
from action_platform.core.flow.repo.history import History
from action_platform.core.flow.repo.runner import GitRunner, checked, subprocess_git
from action_platform.core.flow.repo.sync import Sync, SyncError, _fetch_problem
from action_platform.core.flow.repo.tags import Tags

__all__ = ["GitRunner", "Repository", "SyncError", "_fetch_problem", "subprocess_git"]


class Repository(Sync, Tags, History, WorkingCopy):
    def __init__(self, path: Path, runner: GitRunner = subprocess_git) -> None:
        self.path = Path(path)
        self.runner = runner

    def __repr__(self) -> str:
        return f"Repository({str(self.path)!r})"

    def __fspath__(self) -> str:
        return str(self.path)

    @classmethod
    def init(
        cls, path: Path, branch: str = "main", runner: GitRunner = subprocess_git
    ) -> "Repository":
        repo = cls(path, runner)
        repo.run(["init", "-q", "-b", branch])

        return repo

    @classmethod
    def clone(
        cls,
        url: str,
        path: Path,
        depth: int | None = None,
        branch: str | None = None,
        runner: GitRunner = subprocess_git,
    ) -> "Repository":
        args = ["clone", "--quiet"]

        if depth:
            args += ["--depth", str(depth)]

        if branch:
            args += ["--branch", check_ref(branch)]

        args += ["--end-of-options", url, str(path)]
        checked(runner(args), args)

        return cls(path, runner)

    def exists(self) -> bool:
        return (self.path / ".git").exists()
