"""app.services.configuration.service — platform.toml edits and the commit that lands them."""

from __future__ import annotations

from action_platform.testing.fixtures import git
from tests.support import ApiCase


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
        self.assertFalse(res.json()["mirrored"])
        self.assertEqual(
            self.client.get(f"/api/apps/{id}").json()["deploy"], {"target": "docker"}
        )
        self.assertTrue(self.client.get(f"/api/apps/{id}").json()["clean"])

        exported = self.client.post(f"/api/apps/{id}/manifest/export")
        self.assertTrue(exported.json()["mirrored"])
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
        self.client.post(f"/api/apps/{id}/manifest/export")

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
        self.client.post(f"/api/apps/{id}/manifest/export")

        changes = self.client.get(f"/api/apps/{id}/changes").json()
        self.assertEqual(changes, {"files": ["platform.toml"], "clean": False})

        self.assertEqual(
            self.client.post(f"/api/apps/{id}/discard").json(),
            {"files": [], "clean": True},
        )
        self.assertTrue(self.client.get(f"/api/apps/{id}").json()["clean"])
        kept = self.client.get(f"/api/apps/{id}/manifest").json()
        self.assertIn("[deploy]", kept["content"])
        self.assertFalse(kept["mirrored"])


class DiscardTest(ApiCase):
    def test_discard_drops_edits_but_the_platform_files_come_back(self):
        from action_platform.settings import settings
        from action_platform.testing.fixtures import template_repo

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

        manifest = self.client.get(f"/api/apps/{id}/manifest").json()["content"]
        self.client.put(
            f"/api/apps/{id}/manifest",
            json={"content": manifest.replace('name = "legacy"', 'name = "edited"')},
        )
        self.client.post(f"/api/apps/{id}/manifest/export")

        res = self.client.post(f"/api/apps/{id}/discard")

        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue(res.json()["clean"])

        detail = self.client.get(f"/api/apps/{id}")

        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["project"]["name"], "edited")
        self.assertFalse(detail.json()["clean"])
        self.assertIn(
            "platform.toml", self.client.get(f"/api/apps/{id}/changes").json()["files"]
        )


class InstallPlatformTest(ApiCase):
    def test_install_endpoint_adds_what_is_missing(self):
        from action_platform.settings import settings
        from action_platform.testing.fixtures import template_repo

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
        res = self.client.post(
            f"/api/apps/{id}/install", json={"type": "web", "ci": "gitlab"}
        )

        self.assertEqual(res.status_code, 201, res.text)
        self.assertIn(".gitlab-ci.yml", res.json()["installed"])
        self.assertIn(
            ".gitlab-ci.yml", self.client.get(f"/api/apps/{id}/changes").json()["files"]
        )

    def test_a_clone_that_lost_its_manifest_gets_it_back_on_the_next_request(self):
        from action_platform.settings import settings
        from action_platform.testing.fixtures import template_repo

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


class IdentityWithoutTokenTest(ApiCase):
    def test_a_local_commit_carries_the_organization_identity(self):
        id = self.add_app(on_main=False)
        root = self.workspaces / id
        manifest = self.client.get(f"/api/apps/{id}/manifest").json()["content"]
        self.client.put(
            f"/api/apps/{id}/manifest",
            json={"content": manifest + '\n[services.cache]\nkind = "redis"\n'},
        )
        self.client.post(f"/api/apps/{id}/manifest/export")

        res = self.client.post(
            f"/api/apps/{id}/commit",
            json={
                "message": "chore(platform): add cache",
                "credentials": {
                    "author_name": "Ada",
                    "author_email": "ada@example.com",
                },
            },
        )

        self.assertEqual(res.status_code, 201, res.text)
        self.assertEqual(
            git(root, "log", "-1", "--format=%an <%ae>"), "Ada <ada@example.com>"
        )
