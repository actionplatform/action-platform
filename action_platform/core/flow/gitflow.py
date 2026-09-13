"""Git-flow rules as Python — pure functions over names and messages. The same rules live in ci-scripts/gitflow.sh for hooks and CI; `GitFlow` (workflow.py) applies them to a repository."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

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
RELEASE_RE = re.compile(r"^(chore\(release\): |chore\(platform\): |chore: bootstrap)")


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
