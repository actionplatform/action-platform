"""action_platform.api.repositories.registry — clones into workspaces, refuses what it must, cleans up."""

from __future__ import annotations

from pathlib import Path

from tests.api.support import ApiCase
from tests.support import git


class RegistryTest(ApiCase):
    def setUp(self):
        super().setUp()
        from action_platform.api.db import Database
        from action_platform.api.repositories.registry import DbStore, Registry

        database = Database(f"sqlite:///{self.tmp_path / 'registry.db'}")
        database.migrate()
        self.registry = Registry(DbStore(database), self.tmp_path / "home")

    def test_clones_into_workspace_and_removes(self):
        entry = self.registry.add(self.url)

        self.assertEqual(entry.name, "demo")
        self.assertEqual(entry.default_branch, "feature/1")
        self.assertTrue(
            Path(entry.path).is_relative_to(self.tmp_path / "home" / "workspaces")
        )
        self.assertTrue((Path(entry.path) / "platform.toml").exists())
        self.assertEqual(self.registry.add(self.url).id, entry.id)

        self.registry.remove(entry.id)

        self.assertEqual(self.registry.list(), [])
        self.assertFalse(Path(entry.path).exists())

    def test_refuses_repo_without_platform(self):
        bare = self.tmp_path / "plain"
        bare.mkdir()
        git(bare, "init", "-q")
        (bare / "x").write_text("x")
        git(bare, "add", "x")
        git(bare, "commit", "-q", "-m", "chore: x")

        with self.assertRaisesRegex(Exception, "platform.toml"):
            self.registry.add(bare.as_uri())
        self.assertFalse(any((self.tmp_path / "home" / "workspaces").glob("*")))

    def test_refuses_non_https_url(self):
        with self.assertRaisesRegex(Exception, "https:// only"):
            self.registry.add("/some/local/path")

    def test_refuses_escaping_symlinks(self):
        evil = self.tmp_path / "evil"
        evil.mkdir()
        (evil / "platform.toml").write_text(
            '[project]\nname = "evil"\ntype = "web"\nlanguage = "python"\n'
        )
        (evil / "secrets").symlink_to(self.tmp_path)
        (evil / "inside").symlink_to("platform.toml")
        git(evil, "init", "-q", "-b", "main")
        git(evil, "add", "-A")
        git(evil, "commit", "-q", "-m", "chore: evil")

        res = self.client.post("/api/apps", json={"url": evil.as_uri()})

        self.assertEqual(res.status_code, 400, res.text)
        self.assertIn("symlinks that point outside", res.json()["detail"])
        self.assertIn("secrets", res.json()["detail"])
        self.assertNotIn("inside", res.json()["detail"])
        self.assertEqual(self.client.get("/api/apps").json(), [])
