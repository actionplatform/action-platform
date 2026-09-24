"""How a git command runs: the injectable runner, and the base every command group builds on."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol

from action_platform.core.flow.git import git_env


class GitRunner(Protocol):
    """Runs one git command in a directory and answers the finished process without raising."""

    def __call__(
        self, args: list[str], cwd: Path | None = None
    ) -> subprocess.CompletedProcess: ...


def subprocess_git(
    args: list[str], cwd: Path | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env={**git_env(), "LC_ALL": "C"},
    )


def checked(
    result: subprocess.CompletedProcess, args: list[str]
) -> subprocess.CompletedProcess:
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, ["git", *args], result.stdout, result.stderr
        )

    return result


class GitCommands:
    """A directory and the runner that executes git in it."""

    path: Path
    runner: GitRunner

    def run(self, args: list[str]) -> str:
        return checked(self.attempt(args), args).stdout.strip()

    def attempt(self, args: list[str]) -> subprocess.CompletedProcess:
        """Run without raising; the caller reads returncode/stderr."""
        return self.runner(args, self.path)

    def lookup(
        self,
        args: list[str],
        codes: tuple[int, ...] = (),
        markers: tuple[str, ...] = (),
    ) -> str | None:
        """Stdout of a command whose failure can mean "not there": None when git exits with one of `codes` or says one of `markers`; any other failure raises."""
        result = self.attempt(args)

        if result.returncode == 0:
            return result.stdout.strip()

        if result.returncode in codes or any(m in result.stderr for m in markers):
            return None

        return checked(result, args).stdout.strip()
