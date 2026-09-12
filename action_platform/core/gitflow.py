"""Git-flow rules as Python, for the CLI and the MCP server; the same rules live in ci-scripts/gitflow.sh for hooks and CI."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from action_platform.core import git

KINDS = {
    "feature",
    "bugfix",
    "hotfix",
    "release",
    "support",
    "chore",
    "docs",
    "refactor",
    "test",
    "ci",
    "perf",
}
TYPES = {
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
}
PROTECTED = {"main", "master", "develop"}

BRANCH_RE = re.compile(r"^(?P<kind>[a-z]+)/[A-Za-z0-9][A-Za-z0-9._-]*$")
COMMIT_RE = re.compile(r"^(?P<type>[a-z]+)(\([a-z0-9._/-]+\))?!?: .+")
RELEASE_RE = re.compile(r"^(chore\(release\): |chore: bootstrap)")


@dataclass
class Report:
    branch: str
    problems: list[str] = field(default_factory=list)
    checked_commits: int = 0

    @property
    def ok(self) -> bool:
        return not self.problems


def kind_of(branch: str) -> str | None:
    match = BRANCH_RE.match(branch)

    if match and match.group("kind") in KINDS:
        return match.group("kind")

    return None


def check_branch(branch: str) -> str | None:
    if branch in PROTECTED or kind_of(branch):
        return None

    return (
        f"branch '{branch}' is not git-flow: use <kind>/<code>[-slug], "
        f"kind in {', '.join(sorted(KINDS))}"
    )


def check_commit(message: str) -> str | None:
    subject = message.splitlines()[0] if message else ""

    if subject.startswith(("Merge ", "Revert ")):
        return None

    match = COMMIT_RE.match(subject)

    if match and match.group("type") in TYPES:
        return None

    return f"not a conventional commit: '{subject}'"


def check_protected(branch: str, message: str = "") -> str | None:
    if branch not in PROTECTED or RELEASE_RE.match(message):
        return None

    return (
        f"direct commits on '{branch}' are not allowed — "
        "start a branch: action-platform branch feature <code>"
    )


def allowed_targets(head: str, default: str, has_develop: bool) -> set[str]:
    kind = kind_of(head)

    if kind in {"feature", "bugfix", "chore", "docs", "refactor", "test", "ci", "perf"}:
        return {"develop"} if has_develop else {default}

    if kind in {"release", "hotfix"}:
        return {default, "develop"}

    if head == "develop":
        return {default}

    return set()


def check_target(head: str, base: str, default: str, has_develop: bool) -> str | None:
    allowed = allowed_targets(head, default, has_develop)

    if base in allowed:
        return None

    return f"'{head}' may not merge into '{base}' (allowed: {', '.join(sorted(allowed)) or 'none'})"


def audit(cwd: Path, since: str | None = None) -> Report:
    """Check the current branch and its commits since `since` (default: the merge base with the default branch)."""
    branch = git.current_branch(cwd=cwd)
    report = Report(branch=branch)

    problem = check_branch(branch)
    if problem:
        report.problems.append(problem)

    base = since or _merge_base(cwd, branch)
    commits = git.commits_since(base, cwd=cwd) if base else []
    report.checked_commits = len(commits)

    for subject in commits:
        problem = check_commit(subject)
        if problem:
            report.problems.append(problem)

        problem = check_protected(branch, subject)
        if problem and problem not in report.problems:
            report.problems.append(problem)

    return report


def install_hooks(cwd: Path) -> bool:
    """Point core.hooksPath at .githooks when the project ships it."""
    hooks = cwd / ".githooks"

    if not hooks.is_dir() or not (cwd / ".git").exists():
        return False

    for hook in hooks.iterdir():
        hook.chmod(0o755)

    git.run(["config", "core.hooksPath", ".githooks"], cwd=cwd)

    return True


def _merge_base(cwd: Path, branch: str) -> str | None:
    if branch in PROTECTED:
        return git.latest_tag(cwd=cwd)

    for candidate in (
        "origin/develop",
        "develop",
        "origin/main",
        "main",
        "origin/master",
        "master",
    ):
        try:
            return git.run(["merge-base", branch, candidate], cwd=cwd)
        except subprocess.CalledProcessError:
            continue

    return None
