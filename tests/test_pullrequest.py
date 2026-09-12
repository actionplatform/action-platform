"""Pull request proposal from a git-flow branch."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from action_platform.core.flow import pullrequest
from action_platform.core.flow.pullrequest import PullRequestError


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
    _git(work, "commit", "-q", "--allow-empty", "-m", "chore: bootstrap")
    _git(work, "push", "-q", "-u", "origin", "main")
    _git(work, "checkout", "-qb", "develop")
    _git(work, "push", "-q", "-u", "origin", "develop")
    _git(work, "checkout", "-qb", "feature/7-login")
    _git(work, "commit", "-q", "--allow-empty", "-m", "feat(login): form")
    _git(work, "commit", "-q", "--allow-empty", "-m", "test(login): cover form")
    _git(work, "commit", "-q", "--allow-empty", "-m", "fix(login): trim email")

    return work


def test_proposal_targets_develop_and_describes_commits(repo: Path):
    proposal = pullrequest.propose(repo)

    assert proposal.head == "feature/7-login"
    assert proposal.base == "develop"
    assert proposal.title == "feat(login): form"
    assert "### Features" in proposal.body and "**login:** form" in proposal.body
    assert "### Bug Fixes" in proposal.body
    assert len(proposal.commits) == 3


def test_hotfix_targets_main(repo: Path):
    _git(repo, "checkout", "-q", "main")
    _git(repo, "checkout", "-qb", "hotfix/9")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "fix: prod is down")

    assert pullrequest.propose(repo).base == "main"


def test_refuses_wrong_target_and_protected_head(repo: Path):
    with pytest.raises(PullRequestError, match="may not merge"):
        pullrequest.propose(repo, base="main")

    _git(repo, "checkout", "-q", "main")

    with pytest.raises(PullRequestError, match="protected"):
        pullrequest.propose(repo)


def test_refuses_bad_commits(repo: Path):
    _git(repo, "commit", "-q", "--allow-empty", "-m", "wip")

    with pytest.raises(PullRequestError, match="git-flow"):
        pullrequest.propose(repo)


def test_open_pushes_and_calls_host(repo: Path, monkeypatch):
    (repo / "platform.toml").write_text(
        '[project]\nname = "x"\n[source_host]\nkind = "github"\nrepo = "acme/x"\n'
    )
    _git(repo, "add", "platform.toml")
    _git(repo, "commit", "-q", "-m", "chore(platform): install")
    calls = {}

    class Host:
        name = "fake"
        repo = "acme/x"

        def open_pr(self, ctx, base, head, title, body, draft=False):
            calls.update(base=base, head=head, title=title, draft=draft)
            from action_platform.core.context import PRRef

            return PRRef(number=1, url="https://example.com/pr/1")

    monkeypatch.setattr(
        pullrequest.Config,
        "from_toml",
        classmethod(lambda cls, p: type("C", (), {"source_host": Host()})()),
    )

    ref = pullrequest.open_pr(repo, draft=True)

    assert ref.number == 1
    assert calls == {
        "base": "develop",
        "head": "feature/7-login",
        "title": "feat(login): form",
        "draft": True,
    }
    assert "feature/7-login" in _git(repo, "ls-remote", "--heads", "origin")
