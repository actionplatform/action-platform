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


class CredentialsArriveWithTheRequestTest(ApiCase):
    def test_manifest_with_a_source_host_loads_without_a_token(self):
        from unittest import mock

        from action_platform.settings import settings

        with (
            mock.patch.object(settings, "GITHUB_TOKEN", None),
            mock.patch("shutil.which", lambda _: None),
        ):
            id = self.add_app()
            res = self.client.post(f"/api/apps/{id}/release", json={"level": "patch"})

        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["next"], "1.2.4")
