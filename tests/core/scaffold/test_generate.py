"""action_platform.core.scaffold.generate — pushing a generated project through the source host."""

from __future__ import annotations

from action_platform.core.flow import git
from action_platform.core.scaffold import generate
from tests.support import TempCase


class FakeHost:
    name = "fake"
    repo = "owner/demo"

    def __init__(self) -> None:
        self.created: list = []

    def create_repository(self, repo, description="", private=False):
        self.created.append((repo, description, private))
        return f"https://example.com/{repo}.git"


class PushProjectTest(TempCase):
    def test_bootstraps_git_and_creates_the_remote(self):
        (self.tmp_path / "platform.toml").write_text(
            '[project]\nname = "demo"\nlanguage = "python"\n[source_host]\nkind = "github"\nrepo = "owner/demo"\n'
        )
        (self.tmp_path / "README.md").write_text("# demo\n")
        host = FakeHost()
        pushed: dict = {}
        self.patch(
            generate.Config,
            "from_toml",
            classmethod(lambda cls, p: type("C", (), {"source_host": host})()),
        )
        self.patch(
            git,
            "push_upstream",
            lambda branch, cwd, remote="origin": pushed.update(branch=branch),
        )

        url = generate.push_project(self.tmp_path, private=True)

        self.assertEqual(url, "https://example.com/owner/demo.git")
        self.assertEqual(host.created, [("owner/demo", "", True)])
        self.assertEqual(pushed, {"branch": "main"})
        self.assertTrue(git.is_clean(cwd=self.tmp_path))
        self.assertEqual(git.remote_url(cwd=self.tmp_path), url)
        self.assertEqual(git.current_branch(cwd=self.tmp_path), "main")
