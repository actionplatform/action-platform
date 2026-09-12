"""init --push: local git bootstrap + remote creation through SourceHost, no secrets."""

from pathlib import Path

from action_platform.core.flow import git
from action_platform.core.scaffold import generate


class FakeHost:
    name = "fake"
    repo = "owner/demo"
    created: list = []

    def create_repository(self, repo, description="", private=False):
        self.created.append((repo, description, private))
        return f"https://example.com/{repo}.git"


def test_push_project(tmp_path: Path, monkeypatch):
    (tmp_path / "platform.toml").write_text(
        '[project]\nname = "demo"\nlanguage = "python"\n[source_host]\nkind = "github"\nrepo = "owner/demo"\n'
    )
    (tmp_path / "README.md").write_text("# demo\n")
    pushed = {}
    monkeypatch.setattr(
        generate.Config,
        "from_toml",
        classmethod(lambda cls, p: type("C", (), {"source_host": FakeHost()})()),
    )
    monkeypatch.setattr(
        git,
        "push_upstream",
        lambda branch, cwd, remote="origin": pushed.update(branch=branch),
    )
    monkeypatch.setenv("GIT_AUTHOR_NAME", "t")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "t@t")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "t")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "t@t")

    url = generate.push_project(tmp_path, private=True)

    assert url == "https://example.com/owner/demo.git"
    assert FakeHost.created == [("owner/demo", "", True)]
    assert pushed == {"branch": "main"}
    assert git.is_clean(cwd=tmp_path)
    assert git.remote_url(cwd=tmp_path) == url
    assert git.current_branch(cwd=tmp_path) == "main"
