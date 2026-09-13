"""Branch naming and base resolution against a throwaway origin."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from action_platform.core.flow import branching
from action_platform.core.flow.branching import BranchError, branch_name


def test_branch_name():
    assert branch_name("feature", "42") == "feature/42"
    assert branch_name("hotfix", "PROJ-7", "Fix Login!") == "hotfix/PROJ-7-fix-login"
    assert branch_name("release", "1.4.0") == "release/1.4.0"


def test_branch_name_rejects():
    with pytest.raises(BranchError):
        branch_name("wip", "1")
    with pytest.raises(BranchError):
        branch_name("feature", "bad code")


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    work = tmp_path / "work"
    _git(tmp_path, "clone", "-q", str(origin), str(work))
    (work / "README.md").write_text("x\n")
    _git(work, "add", "README.md")
    _git(work, "commit", "-qm", "chore: init")
    _git(work, "push", "-q", "-u", "origin", "main")

    return work


def test_feature_from_default_when_no_develop(repo: Path):
    branch = branching.start("feature", "42", "login", cwd=repo)

    assert branch.name == "feature/42-login"
    assert branch.base == "main"
    assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "feature/42-login"
    assert "feature/42-login" in _git(repo, "ls-remote", "--heads", "origin")


def test_feature_from_develop_and_hotfix_from_main(repo: Path):
    _git(repo, "checkout", "-qb", "develop")
    _git(repo, "push", "-q", "-u", "origin", "develop")
    _git(repo, "checkout", "-q", "main")

    feature = branching.start("feature", "1", cwd=repo, push=False)
    assert feature.base == "develop"

    _git(repo, "checkout", "-q", "main")
    hotfix = branching.start("hotfix", "2", cwd=repo, push=False)
    assert hotfix.base == "main"


def test_refuses_dirty_tree_and_duplicates(repo: Path):
    branching.start("feature", "9", cwd=repo, push=False)
    _git(repo, "checkout", "-q", "main")

    with pytest.raises(BranchError, match="already exists"):
        branching.start("feature", "9", cwd=repo, push=False)

    (repo / "README.md").write_text("dirty\n")

    with pytest.raises(BranchError, match="dirty"):
        branching.start("feature", "10", cwd=repo, push=False)


def test_default_branch_keeps_slashes(tmp_path, monkeypatch):
    from action_platform.core.flow import branching

    monkeypatch.setattr(
        branching.git, "run", lambda args, cwd=None: "refs/remotes/origin/release/1.2"
    )
    assert branching._default_branch(tmp_path) == "release/1.2"
