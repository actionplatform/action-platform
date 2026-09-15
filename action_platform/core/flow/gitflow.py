"""Git-flow rules as Python — the `Rules` object over names and messages. The same rules live in ci-scripts/gitflow.sh for hooks and CI; `GitFlow` (workflow.py) applies them to a repository. A plugin replaces the `gitflow_rules` slot with a subclass to change kinds, protected branches or the commit format."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from action_platform.core.wiring import slot, wired

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


@slot("gitflow_rules")
class Rules:
    kinds: set[str] = KINDS
    types: set[str] = TYPES
    protected: set[str] = PROTECTED
    develop_based: set[str] = {
        "feature",
        "bugfix",
        "chore",
        "docs",
        "refactor",
        "test",
        "ci",
        "perf",
    }
    main_based: set[str] = {"hotfix", "support"}
    branch_re: re.Pattern = BRANCH_RE
    commit_re: re.Pattern = COMMIT_RE
    release_re: re.Pattern = RELEASE_RE

    def kind_of(self, branch: str) -> str | None:
        match = self.branch_re.match(branch)

        if match and match.group("kind") in self.kinds:
            return match.group("kind")

        return None

    def check_branch(self, branch: str) -> str | None:
        if branch in self.protected or self.kind_of(branch):
            return None

        return (
            f"branch '{branch}' is not git-flow: use <kind>/<code>[-slug], "
            f"kind in {', '.join(sorted(self.kinds))}"
        )

    def check_commit(self, message: str) -> str | None:
        subject = message.splitlines()[0] if message else ""

        if subject.startswith(("Merge ", "Revert ")):
            return None

        match = self.commit_re.match(subject)

        if match and match.group("type") in self.types:
            return None

        return f"not a conventional commit: '{subject}'"

    def check_protected(self, branch: str, message: str = "") -> str | None:
        if branch not in self.protected or self.release_re.match(message):
            return None

        return (
            f"direct commits on '{branch}' are not allowed — "
            "start a branch: action-platform branch feature <code>"
        )

    def allowed_targets(self, head: str, default: str, has_develop: bool) -> set[str]:
        kind = self.kind_of(head)

        if kind in self.develop_based:
            return {"develop"} if has_develop else {default}

        if kind in {"release", "hotfix"}:
            return {default, "develop"}

        if head == "develop":
            return {default}

        return set()

    def check_target(
        self, head: str, base: str, default: str, has_develop: bool
    ) -> str | None:
        allowed = self.allowed_targets(head, default, has_develop)

        if base in allowed:
            return None

        return f"'{head}' may not merge into '{base}' (allowed: {', '.join(sorted(allowed)) or 'none'})"


def current() -> Rules:
    return wired.gitflow_rules()


def kind_of(branch: str) -> str | None:
    return current().kind_of(branch)


def check_branch(branch: str) -> str | None:
    return current().check_branch(branch)


def check_commit(message: str) -> str | None:
    return current().check_commit(message)


def check_protected(branch: str, message: str = "") -> str | None:
    return current().check_protected(branch, message)


def allowed_targets(head: str, default: str, has_develop: bool) -> set[str]:
    return current().allowed_targets(head, default, has_develop)


def check_target(head: str, base: str, default: str, has_develop: bool) -> str | None:
    return current().check_target(head, base, default, has_develop)
