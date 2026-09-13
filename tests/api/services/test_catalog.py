"""action_platform.api.services.catalog — the official matrix merged with an organization's template sources."""

from __future__ import annotations

from pathlib import Path

from action_platform.settings import settings
from tests.api.support import ApiCase
from tests.support import git, template_repo


class CatalogCase(ApiCase):
    def setUp(self):
        super().setUp()
        self.patch(
            settings, "TEMPLATES_DIR", str(template_repo(self.tmp_path / "official"))
        )

    def committed(self, root: Path, branch: str = "v1") -> Path:
        git(root, "init", "-q", "-b", branch)
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "chore: templates")
        return root


class MergedMatrixTest(CatalogCase):
    def test_custom_catalog_and_broken_source(self):
        custom = self.committed(
            template_repo(self.tmp_path / "custom", stack="go", template="gin")
        )

        res = self.client.post(
            "/api/matrix",
            json={
                "sources": [
                    {"name": "acme", "url": custom.as_uri(), "ref": "v1"},
                    {"name": "broken", "url": (self.tmp_path / "missing").as_uri()},
                ]
            },
        )

        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        sources = {s["name"]: s for s in body["sources"]}
        self.assertTrue(sources["official"]["ok"])
        self.assertTrue(sources["acme"]["ok"])
        self.assertFalse(sources["broken"]["ok"])
        self.assertTrue(sources["broken"]["error"])
        by_source = {(p["source"], p["stack"]) for p in body["projects"]}
        self.assertIn(("official", "python"), by_source)
        self.assertIn(("acme", "go"), by_source)

    def test_plain_repository_is_one_template_and_generates(self):
        plain = self.tmp_path / "starter"
        (plain / "app").mkdir(parents=True)
        (plain / "app" / "main.py").write_text("print('hi')\n")
        (plain / "pyproject.toml").write_text('[project]\nname = "starter"\n')
        self.committed(plain, branch="main")
        spec = {"name": "starter", "url": plain.as_uri(), "ref": "main"}

        matrix = self.client.post("/api/matrix", json={"sources": [spec]}).json()
        mine = [p for p in matrix["projects"] if p["source"] == "starter"]
        self.assertEqual(len(mine), 1)
        self.assertEqual(
            (mine[0]["stack"], mine[0]["template"], mine[0]["plain"]),
            ("python", "starter", True),
        )

        res = self.client.post(
            "/api/apps/init",
            json={
                "type": "web",
                "stack": "python",
                "template": "starter",
                "name": "My Service",
                "source": spec,
                "push": False,
            },
        )
        self.assertEqual(res.status_code, 201, res.text)
        created = res.json()
        detail = self.client.get(f"/api/apps/{created['id']}").json()
        self.assertEqual(created["name"], "my-service")
        self.assertEqual(detail["project"]["language"], "python")
        self.assertEqual(detail["project"]["type"], "web")
        self.assertTrue((Path(created["path"]) / "app" / "main.py").exists())
        self.assertTrue((Path(created["path"]) / "platform.toml").exists())
        self.assertEqual(
            (Path(created["path"]) / "LAST_VERSION").read_text(), "0.0.0\n"
        )

    def test_source_ref_is_validated(self):
        res = self.client.post(
            "/api/matrix",
            json={
                "sources": [
                    {
                        "name": "evil",
                        "url": self.url,
                        "ref": "--upload-pack=touch /tmp/pwned",
                    }
                ]
            },
        )

        evil = next(s for s in res.json()["sources"] if s["name"] == "evil")
        self.assertFalse(evil["ok"])
        self.assertIn("invalid git ref", evil["error"])
