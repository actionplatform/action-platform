"""Reads come from the snapshot: once taken, the app pages never touch the clone."""

from __future__ import annotations

import shutil
import unittest
from unittest import mock

from action_platform.settings import settings
from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient, "fastapi is not installed")
class SnapshotTest(GateCase):
    def test_first_read_takes_it_and_later_reads_skip_git(self):
        from action_platform.core.flow.repository import Repository

        registry_id = self.register()
        detail = self.client.get(f"/api/v1/apps/{registry_id}", headers=self.h()).json()
        self.assertIn("snapshot_at", detail)
        commits = self.client.get(
            f"/api/v1/apps/{registry_id}/commits", headers=self.h()
        ).json()
        self.assertTrue(commits)

        shutil.rmtree(settings.WORKSPACES / registry_id, ignore_errors=True)

        with mock.patch.object(
            Repository, "clone", side_effect=AssertionError("a read cloned")
        ):
            for path in (
                "",
                "/gitflow",
                "/commits",
                "/branches",
                "/tags",
                "/releases",
                "/manifest",
            ):
                res = self.client.get(
                    f"/api/v1/apps/{registry_id}{path}", headers=self.h()
                )
                self.assertEqual(res.status_code, 200, f"{path}: {res.text}")

        again = self.client.get(f"/api/v1/apps/{registry_id}", headers=self.h()).json()
        self.assertIsNotNone(again["snapshot_at"])
        self.assertEqual(again["branch"], detail["branch"])

    def test_the_app_list_reads_the_snapshot_when_the_clone_is_gone(self):
        registry_id = self.register()
        self.client.get(f"/api/v1/apps/{registry_id}", headers=self.h())
        shutil.rmtree(settings.WORKSPACES / registry_id, ignore_errors=True)

        rows = self.client.get("/api/v1/apps", headers=self.h()).json()
        row = next(r for r in rows if r["id"] == registry_id)

        self.assertEqual((row["type"], row["language"]), ("web", "python"))
        self.assertEqual(row["last_version"], "1.2.3")
        self.assertEqual(row["branch"], "main")

    def test_sync_retakes_the_snapshot(self):
        from app.repositories.workspace.snapshots import SnapshotStore

        registry_id = self.register()
        self.client.get(f"/api/v1/apps/{registry_id}", headers=self.h())
        before = SnapshotStore(self.app.state.db).get(registry_id)
        self.assertIsNotNone(before)

        res = self.client.post(
            f"/api/v1/apps/{registry_id}/sync", json={}, headers=self.h()
        )
        self.assertIn(res.status_code, (200, 202), res.text)

        after = SnapshotStore(self.app.state.db).get(registry_id)
        self.assertIsNotNone(after)
        self.assertGreaterEqual(after[1], before[1])
        self.assertEqual(after[0]["detail"]["id"], registry_id)
