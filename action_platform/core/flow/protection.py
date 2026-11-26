"""Git-flow enforced on the code host: the `[gitflow.protection]` table, the policy a host applies, the state of each rule and the checks a repository's CI reports."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from action_platform.core.exception import ConfigError
from action_platform.core.flow.gitflow import KINDS, PROTECTED, TYPES

GITFLOW_CHECK = "gitflow"
COMMIT_CHECK = "conventional-commit"
PLATFORM_CHECKS = (GITFLOW_CHECK, COMMIT_CHECK)

NATIVE = "native"
CHECK = "check"
INACTIVE = "inactive"

DIRECT_PUSH = "direct_push"
FORCE_PUSH = "force_push"
DELETION = "deletion"
PULL_REQUEST = "pull_request"
REQUIRED_CHECKS = "required_checks"
BRANCH_NAMES = "branch_names"
COMMIT_MESSAGES = "commit_messages"
RULES = (
    DIRECT_PUSH,
    FORCE_PUSH,
    DELETION,
    PULL_REQUEST,
    REQUIRED_CHECKS,
    BRANCH_NAMES,
    COMMIT_MESSAGES,
)
LABELS = {
    DIRECT_PUSH: "Direct push blocked",
    FORCE_PUSH: "Force push blocked",
    DELETION: "Deletion blocked",
    PULL_REQUEST: "Pull request required",
    REQUIRED_CHECKS: "Required checks",
    BRANCH_NAMES: "Branch names",
    COMMIT_MESSAGES: "Conventional Commits",
}

BRANCH_PATTERN = (
    r"^(main|master|develop|(dependabot|renovate)/.+|("
    + "|".join(sorted(KINDS))
    + r")/[A-Za-z0-9][A-Za-z0-9._-]*)$"
)
COMMIT_PATTERN = (
    r'^(Merge |Revert "|(' + "|".join(sorted(TYPES)) + r")(\([a-z0-9._/-]+\))?!?: .+)"
)

GITHUB_JOB = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")
GITHUB_JOB_NAME = re.compile(r"^    name:\s*[\"']?([^\"'#]+?)[\"']?\s*(#.*)?$")
GITLAB_JOB = re.compile(r"^([A-Za-z0-9_-]+):\s*$")
BITBUCKET_STEP = re.compile(r"^\s+name:\s*[\"']?([^\"'#]+?)[\"']?\s*(#.*)?$")


@dataclass(frozen=True)
class ProtectionSpec:
    """`[gitflow.protection]`: `enforce` (None when the table does not say), the branches to protect (empty: the git-flow ones the repository has) and the status checks always required, on top of those the CI declares or reports."""

    enforce: Optional[bool] = None
    branches: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()

    @classmethod
    def parse(cls, gitflow: Any) -> "ProtectionSpec":
        if not gitflow:
            return cls()

        if not isinstance(gitflow, dict):
            raise ConfigError("[gitflow] must be a table")

        table = gitflow.get("protection") or {}

        if not isinstance(table, dict):
            raise ConfigError("[gitflow.protection] must be a table")

        enforce = table.get("enforce")

        if enforce is not None and not isinstance(enforce, bool):
            raise ConfigError("[gitflow.protection] enforce must be true or false")

        return cls(enforce, _names(table, "branches"), _names(table, "checks"))

    def resolved(self, default: bool) -> bool:
        return default if self.enforce is None else self.enforce


def _names(table: dict, key: str) -> tuple[str, ...]:
    names = table.get(key) or []

    if not isinstance(names, list) or not all(
        isinstance(n, str) and n.strip() for n in names
    ):
        raise ConfigError(f"[gitflow.protection] {key} must be a list of names")

    return tuple(dict.fromkeys(n.strip() for n in names))


@dataclass(frozen=True)
class Identity:
    """Who may still push to a protected branch: the platform's own account on the host, never a person."""

    kind: str
    id: str
    name: str


@dataclass(frozen=True)
class Policy:
    branches: tuple[str, ...]
    checks: tuple[str, ...]
    identity: Optional[Identity]
    branch_pattern: str = BRANCH_PATTERN
    commit_pattern: str = COMMIT_PATTERN


@dataclass
class RuleState:
    rule: str
    mode: str
    detail: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "rule": self.rule,
            "label": LABELS[self.rule],
            "mode": self.mode,
            "detail": self.detail,
        }


@dataclass
class ProtectionState:
    """What the host enforces for each rule, what differs from the policy, and why nothing could be applied when that is the case."""

    host: str
    branches: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()
    rules: list[RuleState] = field(default_factory=list)
    drift: list[str] = field(default_factory=list)
    error: Optional[str] = None
    changed_by: Optional[str] = None
    bypass: Optional[str] = None

    @property
    def active(self) -> bool:
        return self.error is None and any(r.mode == NATIVE for r in self.rules)

    def rule(self, name: str) -> Optional[RuleState]:
        return next((r for r in self.rules if r.rule == name), None)

    def set(self, rule: str, mode: str, detail: str = "") -> None:
        self.rules = [r for r in self.rules if r.rule != rule]
        self.rules.append(RuleState(rule, mode, detail))
        self.rules.sort(key=lambda r: RULES.index(r.rule))

    def refuse(self, reason: str) -> "ProtectionState":
        self.error = reason
        self.rules = [RuleState(r, INACTIVE, reason) for r in RULES]

        return self

    def as_dict(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "active": self.active,
            "branches": list(self.branches),
            "checks": list(self.checks),
            "rules": [r.as_dict() for r in self.rules],
            "drift": list(self.drift),
            "error": self.error,
            "changed_by": self.changed_by,
            "bypass": self.bypass,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProtectionState":
        return cls(
            host=data.get("host", ""),
            branches=tuple(data.get("branches") or ()),
            checks=tuple(data.get("checks") or ()),
            rules=[
                RuleState(r["rule"], r["mode"], r.get("detail", ""))
                for r in data.get("rules") or []
                if r.get("rule") in RULES
            ],
            drift=list(data.get("drift") or []),
            error=data.get("error"),
            changed_by=data.get("changed_by"),
            bypass=data.get("bypass"),
        )


def enforce_by_default(file: Path) -> bool:
    """A new project's platform.toml gets `[gitflow.protection] enforce = true` unless it already says; answers whether it was added."""
    text = file.read_text() if file.exists() else ""

    if re.search(r"^\s*\[gitflow(\.protection)?\]", text, re.M):
        return False

    file.write_text(
        text.rstrip("\n")
        + ("\n\n" if text.strip() else "")
        + "[gitflow.protection]\nenforce = true\n"
    )

    return True


def check_rules(state: ProtectionState, policy: Policy, native_names: bool) -> None:
    """Branch names and commit messages: native when the host enforces the patterns, else carried by the required `gitflow` and `conventional-commit` checks when the CI runs them."""
    for rule, check in ((BRANCH_NAMES, GITFLOW_CHECK), (COMMIT_MESSAGES, COMMIT_CHECK)):
        if native_names:
            state.set(rule, NATIVE, "pattern enforced by the host on every push")
        elif check in policy.checks:
            state.set(
                rule, CHECK, f"the required `{check}` check refuses the pull request"
            )
        else:
            state.set(
                rule,
                INACTIVE,
                f"the repository's CI does not report a `{check}` check on pull requests",
            )


def protected_branches(
    spec: ProtectionSpec, existing: Iterable[str]
) -> tuple[str, ...]:
    """The branches to protect: the table's, else main/master/develop among those the repository has."""
    if spec.branches:
        return spec.branches

    have = set(existing)

    return tuple(b for b in ("main", "master", "develop") if b in have)


def declared_checks(root: Path, ci: str = "") -> tuple[str, ...]:
    """The platform checks the repository's CI reports on pull requests, by the name a host requires them under."""
    found: set[str] = set()

    if ci in ("", "github"):
        found |= _github(root / ".github" / "workflows")

    if ci in ("", "gitlab"):
        found |= _gitlab(root / ".gitlab-ci.yml")

    if ci in ("", "bitbucket"):
        found |= _bitbucket(root / "bitbucket-pipelines.yml")

    return tuple(c for c in PLATFORM_CHECKS if c in found)


def _github(workflows: Path) -> set[str]:
    names: set[str] = set()

    if not workflows.is_dir():
        return names

    for file in sorted(workflows.iterdir()):
        if file.suffix not in (".yml", ".yaml"):
            continue

        text = file.read_text(errors="replace")

        if "pull_request" not in text:
            continue

        names |= _github_jobs(text.splitlines())

    return names & set(PLATFORM_CHECKS)


def _github_jobs(lines: list[str]) -> set[str]:
    names: set[str] = set()
    in_jobs = False
    job: Optional[str] = None
    named: Optional[str] = None

    def close() -> None:
        if job is not None:
            names.add(named or job)

    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        if not line.startswith(" "):
            close()
            job, named = None, None
            in_jobs = line.rstrip() == "jobs:"
            continue

        if not in_jobs:
            continue

        match = GITHUB_JOB.match(line)

        if match:
            close()
            job, named = match.group(1), None
            continue

        name = GITHUB_JOB_NAME.match(line)

        if name and job is not None and named is None:
            named = name.group(1).strip()

    close()

    return names


def _gitlab(file: Path) -> set[str]:
    if not file.is_file():
        return set()

    return {
        m.group(1)
        for line in file.read_text(errors="replace").splitlines()
        if (m := GITLAB_JOB.match(line))
    } & set(PLATFORM_CHECKS)


def _bitbucket(file: Path) -> set[str]:
    if not file.is_file():
        return set()

    text = file.read_text(errors="replace")

    if "pull-requests" not in text:
        return set()

    return {
        m.group(1).strip()
        for line in text.splitlines()
        if (m := BITBUCKET_STEP.match(line))
    } & set(PLATFORM_CHECKS)


__all__ = [
    "BRANCH_PATTERN",
    "COMMIT_PATTERN",
    "LABELS",
    "PLATFORM_CHECKS",
    "PROTECTED",
    "RULES",
    "Identity",
    "Policy",
    "ProtectionSpec",
    "ProtectionState",
    "RuleState",
    "check_rules",
    "declared_checks",
    "enforce_by_default",
    "protected_branches",
]
