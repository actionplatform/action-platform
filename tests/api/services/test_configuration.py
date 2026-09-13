"""action_platform.api.services.configuration — platform.toml edits and the commit that lands them."""

from __future__ import annotations

from tests.api.support import ApiCase


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
