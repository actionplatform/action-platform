"""app.services.releases — releases from the current or another branch."""

from __future__ import annotations

from action_platform.testing.fixtures import git
from tests.support import ApiCase


class ReleaseTest(ApiCase):
    def test_dry_run_from_another_branch(self):
        id = self.add_app()

        rc = self.client.post(
            f"/api/apps/{id}/release", json={"level": "minor", "branch": "feature/1"}
        )
        self.assertEqual(rc.status_code, 200, rc.text)
        self.assertEqual(rc.json()["branch"], "feature/1")
        self.assertTrue(rc.json()["prerelease"])
        self.assertTrue(rc.json()["next"].startswith("1.3.0-rc."))

        stable = self.client.post(
            f"/api/apps/{id}/release", json={"level": "minor", "branch": "main"}
        )
        self.assertEqual(stable.status_code, 200, stable.text)
        self.assertEqual(stable.json()["branch"], "main")
        self.assertFalse(stable.json()["prerelease"])
        self.assertEqual(stable.json()["next"], "1.3.0")
        self.assertEqual(self.client.get(f"/api/apps/{id}").json()["branch"], "main")


class CredentialsArriveWithTheRequestTest(ApiCase):
    def test_manifest_with_a_source_host_loads_without_a_token(self):
        from unittest import mock

        with (
            mock.patch.dict(
                "os.environ", {"ACTION_PLATFORM_GITHUB_TOKEN": "", "GH_TOKEN": ""}
            ),
            mock.patch("shutil.which", lambda _: None),
        ):
            id = self.add_app()
            res = self.client.post(f"/api/apps/{id}/release", json={"level": "patch"})

        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["next"], "1.2.4")


class GitIdentityTest(ApiCase):
    def test_release_commits_with_the_request_author_or_the_platform_default(self):
        for key in [
            "GIT_AUTHOR_NAME",
            "GIT_AUTHOR_EMAIL",
            "GIT_COMMITTER_NAME",
            "GIT_COMMITTER_EMAIL",
        ]:
            self.delenv(key)
        git(self.repo, "config", "receive.denyCurrentBranch", "updateInstead")
        id = self.add_app()
        self.patch(
            "action_platform.providers.source.github.SourceGithub.create_release",
            value=lambda *a, **k: None,
        )

        res = self.client.post(
            f"/api/apps/{id}/release",
            json={
                "level": "patch",
                "dry_run": False,
                "credentials": {
                    "kind": "github",
                    "token": "x",
                    "author_name": "Ada",
                    "author_email": "ada@example.com",
                },
            },
        )

        self.assertEqual(res.status_code, 200, res.text)
        workspace = next(self.workspaces.glob("*"))
        self.assertEqual(
            git(workspace, "log", "-1", "--format=%an <%ae>"), "Ada <ada@example.com>"
        )


class ReleasePushTest(ApiCase):
    def test_a_rejected_push_rolls_the_release_back(self):
        id = self.add_app()
        root = self.workspaces / id
        before = git(root, "rev-parse", "HEAD")
        git(self.repo, "config", "receive.denyCurrentBranch", "refuse")

        res = self.client.post(
            f"/api/apps/{id}/release", json={"level": "patch", "dry_run": False}
        )

        self.assertEqual(res.status_code, 400, res.text)
        self.assertIn("nothing was published", res.json()["detail"])
        self.assertEqual(git(root, "rev-parse", "HEAD"), before)
        self.assertNotIn("v1.2.4", git(root, "tag"))
        self.assertEqual(git(root, "status", "--porcelain"), "")

    def test_a_workspace_behind_the_remote_is_brought_level_first(self):
        from action_platform.providers.source.github import SourceGithub

        self.patch(SourceGithub, "create_release", lambda *a, **k: None)
        git(self.repo, "config", "receive.denyCurrentBranch", "updateInstead")
        id = self.add_app()
        root = self.workspaces / id
        (self.repo / "b.txt").write_text("b")
        git(self.repo, "add", "b.txt")
        git(self.repo, "commit", "-qm", "feat: add b")

        res = self.client.post(
            f"/api/apps/{id}/release", json={"level": "patch", "dry_run": False}
        )

        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["next"], "1.2.4")
        self.assertTrue((root / "b.txt").exists())
        self.assertEqual(
            git(self.repo, "log", "-1", "--format=%s"), "chore(release): 1.2.4"
        )
        self.assertIn("v1.2.4", git(self.repo, "tag"))
