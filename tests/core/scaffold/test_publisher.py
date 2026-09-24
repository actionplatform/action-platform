"""action_platform.core.scaffold.publisher — pushing a generated project through the source host."""

from __future__ import annotations

from action_platform.core.flow.repository import Repository
from action_platform.core.scaffold import publisher
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
            publisher.Config,
            "from_toml",
            classmethod(lambda cls, p: type("C", (), {"source_host": host})()),
        )
        self.patch(
            Repository,
            "push_upstream",
            lambda self, branch, remote="origin": pushed.update(branch=branch),
        )

        url = publisher.push_project(self.tmp_path, private=True)
        repo = Repository(self.tmp_path)

        self.assertEqual(url, "https://example.com/owner/demo.git")
        self.assertEqual(host.created, [("owner/demo", "", True)])
        self.assertEqual(pushed, {"branch": "main"})
        self.assertTrue(repo.is_clean())
        self.assertEqual(repo.remote_url(), url)
        self.assertEqual(repo.branch, "main")
