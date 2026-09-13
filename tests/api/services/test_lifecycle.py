"""action_platform.api.services.lifecycle — releases from the current or another branch."""

from __future__ import annotations

from tests.api.support import ApiCase


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
