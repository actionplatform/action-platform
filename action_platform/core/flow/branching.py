"""Start work branches the git-flow way: right base, fresh pull, conventional name."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from action_platform.core.flow import git, gitflow
from action_platform.core.exception import ActionPlatformError

DEVELOP_BASED = {
    "feature",
    "bugfix",
    "chore",
    "docs",
    "refactor",
    "test",
    "ci",
    "perf",
    "release",
}
MAIN_BASED = {"hotfix", "support"}
KINDS = sorted(DEVELOP_BASED | MAIN_BASED)


class BranchError(ActionPlatformError):
    """Cannot start the branch."""


@dataclass
class Branch:
    name: str
    base: str
    pushed: bool = False


def branch_name(kind: str, code: str, slug: str | None = None) -> str:
    if kind not in KINDS:
        raise BranchError(
            f"unknown branch kind: {kind} (available: {', '.join(KINDS)})"
        )

    code = code.strip()

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", code):
        raise BranchError(f"invalid code: {code!r} (letters, digits, . _ -)")

    name = f"{kind}/{code}"

    if slug:
        name += "-" + _slugify(slug)

    return name


def resolve_base(kind: str, cwd: Path) -> str:
    """develop when it exists on origin, else the default branch; hotfix/support always the default."""
    default = _default_branch(cwd)

    if kind in MAIN_BASED:
        return default

    if _remote_has(cwd, "develop"):
        return "develop"

    return default


def start(
    kind: str,
    code: str,
    slug: str | None = None,
    cwd: Path | None = None,
    push: bool = True,
) -> Branch:
    cwd = cwd or Path.cwd()

    if not git.is_clean(cwd=cwd):
        raise BranchError("working tree is dirty — commit or stash first")

    gitflow.install_hooks(cwd)
    name = branch_name(kind, code, slug)
    git.run(["fetch", "--prune", "origin"], cwd=cwd)

    if _remote_has(cwd, name) or _local_has(cwd, name):
        raise BranchError(f"branch {name} already exists")

    base = resolve_base(kind, cwd)
    git.checkout_branch(base, cwd=cwd)
    git.run(["pull", "--ff-only", "origin", base], cwd=cwd)
    git.checkout_branch(name, create=True, cwd=cwd)

    if push:
        git.push_upstream(name, cwd)

    return Branch(name=name, base=base, pushed=push)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _default_branch(cwd: Path) -> str:
    try:
        ref = git.run(["symbolic-ref", "refs/remotes/origin/HEAD"], cwd=cwd)
        return ref.removeprefix("refs/remotes/origin/")
    except subprocess.CalledProcessError:
        pass

    for candidate in ("main", "master"):
        if _remote_has(cwd, candidate) or _local_has(cwd, candidate):
            return candidate

    raise BranchError("cannot find a default branch (main or master)")


def _remote_has(cwd: Path, branch: str) -> bool:
    out = git.run(["ls-remote", "--heads", "origin", branch], cwd=cwd)

    return bool(out.strip())


def _local_has(cwd: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=cwd,
        capture_output=True,
        env=git.git_env(),
    )

    return result.returncode == 0
