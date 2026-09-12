"""Release: rc off main, stable on main, refuses existing tags before touching files."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from action_platform.core.flow import git
from action_platform.core.release import release as releasing
from action_platform.core.config import Config
from action_platform.core.exception import ReleaseError


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch) -> Path:
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    work = tmp_path / "work"
    _git(tmp_path, "clone", "-q", str(origin), str(work))
    (work / "LAST_VERSION").write_text("0.3.1\n")
    (work / "platform.toml").write_text('[project]\nname = "x"\n')
    _git(work, "add", "-A")
    _git(work, "commit", "-qm", "chore: bootstrap")
    _git(work, "push", "-q", "-u", "origin", "main")
    _git(work, "tag", "v0.3.1")
    _git(work, "commit", "-q", "--allow-empty", "-m", "feat: x")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "t")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "t@t")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "t")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "t@t")

    return work


def _release(repo: Path, level: str, prerelease=None):
    return releasing.release(Config(), level, repo, prerelease=prerelease)


def test_stable_on_main(repo: Path):
    ctx = _release(repo, "patch")

    assert ctx.next_version == "0.3.2"
    assert "v0.3.2" in git.tags(cwd=repo)


def test_rc_off_main_and_increments(repo: Path):
    _git(repo, "checkout", "-qb", "feature/1")

    first = _release(repo, "patch")
    assert first.next_version == "0.3.2-rc.1"

    _git(repo, "commit", "-q", "--allow-empty", "-m", "fix: y")
    second = _release(repo, "patch")
    assert second.next_version == "0.3.2-rc.2"


def test_existing_tag_refused_before_writing(repo: Path):
    _git(repo, "tag", "v0.3.2")
    before = _git(repo, "rev-parse", "HEAD")

    with pytest.raises(ReleaseError, match="already exists"):
        _release(repo, "patch")

    assert _git(repo, "rev-parse", "HEAD") == before
    assert (repo / "LAST_VERSION").read_text() == "0.3.1\n"
    assert not (repo / "CHANGELOG.md").exists()


def test_same_version_refused(repo: Path):
    _git(repo, "tag", "-d", "v0.3.1")

    with pytest.raises(ReleaseError, match="already the current version"):
        _release(repo, "0.3.1")
