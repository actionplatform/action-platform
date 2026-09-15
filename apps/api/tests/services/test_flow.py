"""action_platform_api.services.workspace.flow — branches, checkout and pull requests on the platform's clone."""

from __future__ import annotations

import shutil

from tests.support import ApiCase
from action_platform.testing.fixtures import git


class FlowTest(ApiCase):
    def test_start_branch_and_checkout(self):
        id = self.add_app()

        res = self.client.post(
            f"/api/apps/{id}/branches",
            json={"kind": "feature", "code": "7", "slug": "login"},
        )
        self.assertEqual(res.status_code, 201, res.text)
        self.assertEqual(
            res.json(), {"branch": "feature/7-login", "base": "main", "pushed": True}
        )
        self.assertEqual(
            self.client.get(f"/api/apps/{id}").json()["branch"], "feature/7-login"
        )
        self.assertIn("feature/7-login", git(self.repo, "branch", "--list"))

        shutil.rmtree(self.workspaces / id)
        self.assertEqual(
            self.client.get(f"/api/apps/{id}").json()["branch"], "feature/7-login"
        )

        self.assertEqual(
            self.client.post(
                f"/api/apps/{id}/checkout", json={"branch": "main"}
            ).json()["branch"],
            "main",
        )
        self.assertEqual(
            self.client.post(
                f"/api/apps/{id}/branches",
                json={"kind": "wip", "code": "1", "push": False},
            ).status_code,
            400,
        )

    def test_propose_pull_request(self):
        id = self.add_app()
        self.client.post(f"/api/apps/{id}/checkout", json={"branch": "feature/1"})

        res = self.client.get(f"/api/apps/{id}/pull-request")

        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(body["head"], "feature/1")
        self.assertEqual(body["base"], "main")
        self.assertTrue(
            "feat: add a" in body["title"] or body["commits"] == ["feat: add a"]
        )

    def test_refs_that_look_like_options_are_refused(self):
        id = self.add_app()

        for bad in [
            "--upload-pack=touch /tmp/pwned",
            "-x",
            "a..b",
            "feature/@{1}",
            "x.lock",
            "dir/",
        ]:
            self.assertEqual(
                self.client.post(
                    f"/api/apps/{id}/checkout", json={"branch": bad}
                ).status_code,
                400,
                bad,
            )
            self.assertEqual(
                self.client.post(
                    f"/api/apps/{id}/release", json={"level": "patch", "branch": bad}
                ).status_code,
                400,
                bad,
            )

    def test_dirty_tree_blocks_checkout_and_branching(self):
        id = self.add_app()
        content = self.client.get(f"/api/apps/{id}/manifest").json()["content"]
        self.client.put(
            f"/api/apps/{id}/manifest",
            json={"content": content + '\n[deploy]\ntarget = "docker"\n'},
        )

        self.assertEqual(
            self.client.post(
                f"/api/apps/{id}/checkout", json={"branch": "feature/1"}
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.post(
                f"/api/apps/{id}/release",
                json={"level": "patch", "branch": "feature/1"},
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.post(
                f"/api/apps/{id}/branches",
                json={"kind": "chore", "code": "9", "push": False},
            ).status_code,
            400,
        )


class ProposeWithoutRemoteAccessTest(ApiCase):
    def test_a_remote_that_cannot_be_reached_is_a_400_with_a_reason(self):
        id = self.add_app(on_main=False)
        root = self.workspaces / id
        git(root, "remote", "set-url", "origin", "https://github.com/acme/private.git")

        res = self.client.get(f"/api/apps/{id}/pull-request")

        self.assertEqual(res.status_code, 400, res.text)
        self.assertIn("code host", res.json()["detail"])
