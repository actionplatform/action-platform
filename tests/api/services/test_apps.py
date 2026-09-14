"""action_platform.api.services.apps — register, inspect, sync, generate and import apps."""

from __future__ import annotations

import shutil
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

    def test_a_branch_made_by_hand_in_the_clone_does_not_survive(self):
        id = self.add_app()
        workspace = next(self.workspaces.glob("*"))
        git(workspace, "checkout", "-q", "-b", "chore/7-local-only")

        self.assertEqual(self.client.post(f"/api/apps/{id}/sync").status_code, 200)
        self.assertEqual(self.client.get(f"/api/apps/{id}").json()["branch"], "main")

    def test_the_clone_is_rebuilt_when_it_is_gone(self):
        id = self.add_app()
        shutil.rmtree(self.workspaces / id)

        detail = self.client.get(f"/api/apps/{id}").json()

        self.assertEqual(detail["branch"], "main")
        self.assertTrue((self.workspaces / id / "platform.toml").exists())


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
        self.fake_push()

    def test_generates_pushes_and_registers(self):
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
                "credentials": {"kind": "github", "token": "t", "owner": "acme"},
            },
        )

        self.assertEqual(res.status_code, 201, res.text)
        body = res.json()
        self.assertEqual(body["name"], "orders-api")
        self.assertTrue(body["pushed"])
        self.assertTrue(body["url"].endswith(".git"))

        path = Path(body["path"])
        self.assertTrue(path.is_relative_to(self.workspaces))
        self.assertTrue((path / "orders" / "__init__.py").exists())
        self.assertIn("orders", (path / "README.md").read_text())
        self.assertIn('ci = "gitlab"', (path / "platform.toml").read_text())
        self.assertIn('repo = "acme/orders-api"', (path / "platform.toml").read_text())
        self.assertFalse(
            any(p.name.startswith(".init-") for p in path.parent.iterdir())
        )

        shutil.rmtree(path)
        detail = self.client.get(f"/api/apps/{body['id']}").json()
        self.assertEqual(detail["branch"], "main")
        self.assertTrue(detail["clean"])
        self.assertTrue((path / "orders" / "__init__.py").exists())
        self.assertEqual(self.client.get("/api/apps").json()[0]["name"], "orders-api")

    def test_needs_a_host_to_push_to(self):
        res = self.client.post(
            "/api/apps/init",
            json={"type": "web", "stack": "python", "name": "plain"},
        )

        self.assertEqual(res.status_code, 400)
        self.assertIn("source host", res.json()["detail"])
        self.assertEqual(self.client.get("/api/apps").json(), [])

    def test_unknown_type_is_400(self):
        res = self.client.post("/api/apps/init", json={"type": "nope", "name": "x"})

        self.assertEqual(res.status_code, 400)
        self.assertIn("unknown type", res.json()["detail"])


class LegacyImportCase(ApiCase):
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


class ImportWithInstallTest(LegacyImportCase):
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
        self.assertIn(
            "platform.toml",
            self.client.get(f"/api/apps/{body['id']}/changes").json()["files"],
        )


class DraftsSurviveSyncTest(LegacyImportCase):
    def _import(self) -> str:
        return self.client.post(
            "/api/apps",
            json={
                "url": self.bare.as_uri(),
                "install": {"type": "web", "ci": "github"},
            },
        ).json()["id"]

    def test_files_the_remote_now_has_leave_the_draft(self):
        id = self._import()
        root = self.workspaces / id
        for rel in ("platform.toml", ".last_version"):
            if (root / rel).exists():
                (self.bare / rel).write_text((root / rel).read_text())
        git(self.bare, "add", "-A")
        git(self.bare, "commit", "-q", "-m", "chore: install platform")

        res = self.client.post(f"/api/apps/{id}/sync")

        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(
            git(root, "log", "-1", "--format=%s"), "chore: install platform"
        )
        self.assertNotIn(
            "platform.toml", self.client.get(f"/api/apps/{id}/changes").json()["files"]
        )

    def test_a_draft_survives_a_sync_and_a_lost_clone(self):
        id = self._import()
        root = self.workspaces / id
        manifest = self.client.get(f"/api/apps/{id}/manifest").json()["content"]
        self.client.put(
            f"/api/apps/{id}/manifest",
            json={
                "content": manifest.replace('name = "legacy"', 'name = "legacy-local"')
            },
        )
        (self.bare / "README.md").write_text("# legacy\n")
        git(self.bare, "add", "-A")
        git(self.bare, "commit", "-q", "-m", "docs: readme")

        res = self.client.post(f"/api/apps/{id}/sync")

        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue((root / "README.md").exists())
        self.assertIn("legacy-local", (root / "platform.toml").read_text())

        shutil.rmtree(root)

        self.assertIn(
            "legacy-local",
            self.client.get(f"/api/apps/{id}/manifest").json()["content"],
        )


class SyncDivergedTest(ApiCase):
    def test_a_local_commit_the_remote_lacks_is_dropped_for_the_remote(self):
        id = self.add_app(on_main=True)
        root = self.workspaces / id
        (root / "local.txt").write_text("x\n")
        git(root, "add", "local.txt")
        git(root, "commit", "-qm", "feat: local only")
        (self.repo / "remote.txt").write_text("y\n")
        git(self.repo, "add", "remote.txt")
        git(self.repo, "commit", "-qm", "feat: remote only")

        res = self.client.post(f"/api/apps/{id}/sync")

        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue((root / "remote.txt").exists())
        self.assertFalse((root / "local.txt").exists())
        self.assertEqual(git(root, "log", "-1", "--format=%s"), "feat: remote only")

    def test_a_merged_branch_deleted_on_the_remote_returns_to_main(self):
        id = self.add_app(on_main=False)
        root = self.workspaces / id
        self.assertEqual(git(root, "rev-parse", "--abbrev-ref", "HEAD"), "feature/1")
        git(self.repo, "checkout", "-q", "main")
        git(
            self.repo,
            "merge",
            "-q",
            "--no-ff",
            "-m",
            "Merge pull request #1",
            "feature/1",
        )
        git(self.repo, "branch", "-q", "-D", "feature/1")

        res = self.client.post(f"/api/apps/{id}/sync")

        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(git(root, "rev-parse", "--abbrev-ref", "HEAD"), "main")
        self.assertEqual(git(root, "log", "-1", "--format=%s"), "Merge pull request #1")
        self.assertEqual(self.client.get(f"/api/apps/{id}").json()["branch"], "main")


class SyncWithoutAccessTest(ApiCase):
    def test_a_fetch_the_host_refuses_is_a_400_with_a_reason(self):
        id = self.add_app()
        root = self.workspaces / id
        git(root, "remote", "set-url", "origin", "https://github.com/acme/private.git")

        res = self.client.post(f"/api/apps/{id}/sync")

        self.assertEqual(res.status_code, 400, res.text)
        self.assertIn("code host", res.json()["detail"])
