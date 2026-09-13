"""action_platform.api.services.apps — register, inspect, sync, generate and import apps."""

from __future__ import annotations

from pathlib import Path

from action_platform.settings import settings
from tests.api.support import ApiCase
from tests.support import git, template_repo


class AppsCrudTest(ApiCase):
    def test_add_list_sync_remove(self):
        self.assertEqual(self.client.get("/api/apps").json(), [])

        created = self.client.post("/api/apps", json={"url": self.url})
        self.assertEqual(created.status_code, 201)
        id = created.json()["id"]

        rows = self.client.get("/api/apps").json()
        self.assertEqual(rows[0]["name"], "demo")
        self.assertEqual(rows[0]["url"], self.url)
        self.assertEqual(rows[0]["branch"], "feature/1")
        self.assertEqual(rows[0]["last_version"], "1.2.3")

        self.assertEqual(self.client.post(f"/api/apps/{id}/sync").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/apps/{id}").status_code, 204)
        self.assertEqual(self.client.get(f"/api/apps/{id}").status_code, 400)

    def test_detail_and_git_state(self):
        id = self.add_app(on_main=False)

        detail = self.client.get(f"/api/apps/{id}").json()
        self.assertEqual(detail["project"]["name"], "demo")
        self.assertEqual(detail["url"], self.url)
        self.assertEqual(detail["source_host"]["repo"], "acme/demo")
        self.assertEqual(detail["latest_tag"], "v1.2.3")
        self.assertTrue(detail["clean"])

        audit = self.client.get(f"/api/apps/{id}/gitflow").json()
        self.assertTrue(audit["ok"])
        self.assertEqual(audit["checked_commits"], 1)

        self.assertEqual(
            self.client.get(f"/api/apps/{id}/commits?limit=5").json()[0]["subject"],
            "feat: add a",
        )

        branches = {
            b["name"]: b for b in self.client.get(f"/api/apps/{id}/branches").json()
        }
        self.assertTrue(branches["main"]["protected"])
        self.assertEqual(branches["feature/1"]["kind"], "feature")
        self.assertEqual(self.client.get(f"/api/apps/{id}/tags").json(), ["v1.2.3"])

    def test_releases_from_tags(self):
        id = self.add_app(on_main=False)

        rows = self.client.get(f"/api/apps/{id}/releases").json()

        self.assertEqual(rows[0]["tag"], "v1.2.3")
        self.assertEqual(rows[0]["version"], "1.2.3")
        self.assertTrue(rows[0]["latest"])
        self.assertFalse(rows[0]["prerelease"])
        self.assertEqual(len(rows[0]["sha"]), 7)

    def test_sync_without_upstream_is_a_noop(self):
        id = self.add_app()
        workspace = next(self.workspaces.glob("*"))
        git(workspace, "checkout", "-q", "-b", "chore/7-local-only")

        self.assertEqual(self.client.post(f"/api/apps/{id}/sync").status_code, 200)
        self.assertEqual(
            self.client.get(f"/api/apps/{id}").json()["branch"], "chore/7-local-only"
        )


class UrlPolicyTest(ApiCase):
    def test_only_https_urls_are_cloned(self):
        self.patch(settings, "ALLOW_FILE_URLS", False)

        for bad in [
            self.url,
            "ssh://git@github.com/acme/repo.git",
            "git@github.com:acme/repo.git",
            "/tmp/repo",
        ]:
            res = self.client.post("/api/apps", json={"url": bad})
            self.assertEqual(res.status_code, 400, bad)
            self.assertIn("https:// only", res.json()["detail"])

        self.patch(settings, "GIT_HOSTS", ["github.com"])
        res = self.client.post(
            "/api/apps", json={"url": "https://gitlab.com/acme/repo.git"}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("not allowed", res.json()["detail"])


class InitTest(ApiCase):
    def setUp(self):
        super().setUp()
        self.templates = template_repo(
            self.tmp_path / "templates", template="mini", rendered=True
        )
        self.patch(settings, "TEMPLATES_DIR", str(self.templates))

    def test_generates_a_workspace(self):
        res = self.client.post(
            "/api/apps/init",
            json={
                "type": "web",
                "stack": "python",
                "template": "mini",
                "name": "Orders Api",
                "description": "orders",
                "package_name": "orders",
                "ci": "gitlab",
                "git_init": True,
            },
        )

        self.assertEqual(res.status_code, 201, res.text)
        body = res.json()
        self.assertEqual(body["name"], "orders-api")
        self.assertFalse(body["pushed"])
        self.assertEqual(body["url"], "")

        path = Path(body["path"])
        self.assertTrue(path.is_relative_to(self.workspaces))
        self.assertTrue((path / "orders" / "__init__.py").exists())
        self.assertIn("orders", (path / "README.md").read_text())
        self.assertIn('ci = "gitlab"', (path / "platform.toml").read_text())
        self.assertTrue((path / ".git").is_dir())
        self.assertFalse(
            any(p.name.startswith(".init-") for p in path.parent.iterdir())
        )

        detail = self.client.get(f"/api/apps/{body['id']}").json()
        self.assertEqual(detail["branch"], "main")
        self.assertTrue(detail["clean"])
        self.assertEqual(self.client.get("/api/apps").json()[0]["name"], "orders-api")

    def test_without_git(self):
        body = self.client.post(
            "/api/apps/init",
            json={"type": "web", "stack": "python", "name": "plain", "git_init": False},
        ).json()

        self.assertFalse((Path(body["path"]) / ".git").exists())
        self.assertEqual(
            self.client.get(f"/api/apps/{body['id']}").json()["branch"], ""
        )

    def test_unknown_type_is_400(self):
        res = self.client.post("/api/apps/init", json={"type": "nope", "name": "x"})

        self.assertEqual(res.status_code, 400)
        self.assertIn("unknown type", res.json()["detail"])


class ImportWithInstallTest(ApiCase):
    def setUp(self):
        super().setUp()
        self.patch(
            settings, "TEMPLATES_DIR", str(template_repo(self.tmp_path / "official"))
        )
        self.bare = self.tmp_path / "legacy"
        self.bare.mkdir()
        (self.bare / "pyproject.toml").write_text('[project]\nname = "legacy"\n')
        git(self.bare, "init", "-q", "-b", "main")
        git(self.bare, "add", "-A")
        git(self.bare, "commit", "-q", "-m", "chore: legacy")

    def test_refused_without_install_then_installed(self):
        refused = self.client.post("/api/apps", json={"url": self.bare.as_uri()})
        self.assertEqual(refused.status_code, 422)
        self.assertEqual(refused.json()["detail"]["code"], "needs_install")

        res = self.client.post(
            "/api/apps",
            json={
                "url": self.bare.as_uri(),
                "install": {"type": "web", "ci": "github"},
            },
        )
        self.assertEqual(res.status_code, 201, res.text)
        body = res.json()
        self.assertIn("platform.toml", body["installed"])
        self.assertEqual(body["name"], "legacy")

        detail = self.client.get(f"/api/apps/{body['id']}").json()
        self.assertEqual(detail["project"]["language"], "python")
        self.assertEqual(detail["project"]["name"], "legacy")
        self.assertFalse(detail["clean"])
