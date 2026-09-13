"""action_platform.api.services.configuration — platform.toml edits and the commit that lands them."""

from __future__ import annotations

from tests.api.support import ApiCase
from tests.support import git


class ManifestTest(ApiCase):
    def test_read_write_and_commit_on_main(self):
        id = self.add_app()

        content = self.client.get(f"/api/apps/{id}/manifest").json()["content"]
        self.assertIn('name = "demo"', content)

        self.assertEqual(
            self.client.put(
                f"/api/apps/{id}/manifest", json={"content": "[project\nname = "}
            ).status_code,
            400,
        )

        res = self.client.put(
            f"/api/apps/{id}/manifest",
            json={"content": content + '\n[deploy]\ntarget = "docker"\n'},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            self.client.get(f"/api/apps/{id}").json()["deploy"], {"target": "docker"}
        )
        self.assertFalse(self.client.get(f"/api/apps/{id}").json()["clean"])

        self.assertEqual(
            self.client.post(
                f"/api/apps/{id}/commit", json={"message": "update stuff"}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                f"/api/apps/{id}/commit", json={"message": "feat: direct on main"}
            ).status_code,
            400,
        )

        ok = self.client.post(
            f"/api/apps/{id}/commit",
            json={"message": "chore(platform): set docker deploy target"},
        )
        self.assertEqual(ok.status_code, 201, ok.text)
        self.assertTrue(self.client.get(f"/api/apps/{id}").json()["clean"])
        self.assertTrue(
            self.client.get(f"/api/apps/{id}/commits?limit=1")
            .json()[0]["subject"]
            .startswith("chore(platform)")
        )

    def test_commit_on_a_new_branch(self):
        id = self.add_app()
        content = self.client.get(f"/api/apps/{id}/manifest").json()["content"]
        self.client.put(
            f"/api/apps/{id}/manifest",
            json={"content": content + '\n[deploy]\ntarget = "docker"\n'},
        )

        res = self.client.post(
            f"/api/apps/{id}/commit",
            json={
                "message": "chore: set docker deploy target",
                "branch": {"kind": "chore", "code": "42", "slug": "deploy target"},
                "push": True,
            },
        )

        self.assertEqual(res.status_code, 201, res.text)
        body = res.json()
        self.assertEqual(body["branch"], "chore/42-deploy-target")
        self.assertTrue(body["pushed"])
        self.assertIsNone(body["pull_request"])

        state = self.client.get(f"/api/apps/{id}").json()
        self.assertEqual(state["branch"], "chore/42-deploy-target")
        self.assertTrue(state["clean"])
        self.assertEqual(state["deploy"], {"target": "docker"})
        self.assertIn(
            "chore/42-deploy-target",
            {b["name"] for b in self.client.get(f"/api/apps/{id}/branches").json()},
        )

    def test_nothing_to_commit_is_409(self):
        id = self.add_app()

        self.assertEqual(
            self.client.post(
                f"/api/apps/{id}/commit", json={"message": "chore(platform): nothing"}
            ).status_code,
            409,
        )


class ChangesTest(ApiCase):
    def test_lists_and_discards_uncommitted_changes(self):
        id = self.add_app()
        content = self.client.get(f"/api/apps/{id}/manifest").json()["content"]
        self.client.put(
            f"/api/apps/{id}/manifest",
            json={"content": content + '\n[deploy]\ntarget = "docker"\n'},
        )

        changes = self.client.get(f"/api/apps/{id}/changes").json()
        self.assertEqual(changes, {"files": ["platform.toml"], "clean": False})

        self.assertEqual(
            self.client.post(f"/api/apps/{id}/discard").json(),
            {"files": [], "clean": True},
        )
        self.assertTrue(self.client.get(f"/api/apps/{id}").json()["clean"])
        self.assertNotIn(
            "[deploy]", self.client.get(f"/api/apps/{id}/manifest").json()["content"]
        )


class DiscardTest(ApiCase):
    def test_discard_on_an_installed_import_leaves_the_repository_as_cloned(self):
        from action_platform.settings import settings
        from tests.support import template_repo

        self.patch(
            settings, "TEMPLATES_DIR", str(template_repo(self.tmp_path / "official"))
        )
        bare = self.tmp_path / "legacy"
        bare.mkdir()
        (bare / "pyproject.toml").write_text('[project]\nname = "legacy"\n')
        git(bare, "init", "-q", "-b", "main")
        git(bare, "add", "-A")
        git(bare, "commit", "-q", "-m", "chore: legacy")
        id = self.client.post(
            "/api/apps",
            json={"url": bare.as_uri(), "install": {"type": "web", "ci": "github"}},
        ).json()["id"]

        res = self.client.post(f"/api/apps/{id}/discard")

        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue(res.json()["clean"])
        self.assertFalse((self.workspaces / id / "platform.toml").exists())

        detail = self.client.get(f"/api/apps/{id}")

        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["project"]["name"], "legacy")
        self.assertFalse(detail.json()["clean"])


class InstallPlatformTest(ApiCase):
    def test_install_endpoint_writes_the_platform_files_again(self):
        from action_platform.settings import settings
        from tests.support import template_repo

        self.patch(
            settings, "TEMPLATES_DIR", str(template_repo(self.tmp_path / "official"))
        )
        bare = self.tmp_path / "legacy"
        bare.mkdir()
        (bare / "pyproject.toml").write_text('[project]\nname = "legacy"\n')
        git(bare, "init", "-q", "-b", "main")
        git(bare, "add", "-A")
        git(bare, "commit", "-q", "-m", "chore: legacy")
        id = self.client.post(
            "/api/apps",
            json={"url": bare.as_uri(), "install": {"type": "web", "ci": "github"}},
        ).json()["id"]
        (self.workspaces / id / "platform.toml").unlink()

        res = self.client.post(f"/api/apps/{id}/install", json={"type": "web"})

        self.assertEqual(res.status_code, 201, res.text)
        self.assertIn("platform.toml", res.json()["installed"])
        self.assertEqual(self.client.get(f"/api/apps/{id}").status_code, 200)

    def test_a_clone_that_lost_its_manifest_gets_it_back_on_the_next_request(self):
        from action_platform.settings import settings
        from tests.support import template_repo

        self.patch(
            settings, "TEMPLATES_DIR", str(template_repo(self.tmp_path / "official"))
        )
        bare = self.tmp_path / "legacy"
        bare.mkdir()
        (bare / "pyproject.toml").write_text('[project]\nname = "legacy"\n')
        git(bare, "init", "-q", "-b", "main")
        git(bare, "add", "-A")
        git(bare, "commit", "-q", "-m", "chore: legacy")
        id = self.client.post(
            "/api/apps",
            json={"url": bare.as_uri(), "install": {"type": "web", "ci": "github"}},
        ).json()["id"]
        (self.workspaces / id / "platform.toml").unlink()

        res = self.client.get(f"/api/apps/{id}/manifest")

        self.assertEqual(res.status_code, 200, res.text)
        self.assertIn("[project]", res.json()["content"])
        self.assertTrue((self.workspaces / id / "platform.toml").exists())
