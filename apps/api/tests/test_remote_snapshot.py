"""Sync without a clone: the snapshot comes from git ls-remote and the host's API, and stays put while no ref moves."""

from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

TOML = '[project]\nname = "demo"\ntype = "web"\nlanguage = "python"\n'


@unittest.skipUnless(TestClient, "fastapi is not installed")
class RemoteSnapshotTest(GateCase):
    def setUp(self):
        super().setUp()
        from app.core.db.models import RegistryEntry
        from app.repositories.workspace.source import get_registry

        self.registry_id = self.register()

        with self.app.state.db.session() as s:
            s.get(
                RegistryEntry, self.registry_id
            ).url = "https://github.com/acme/demo.git"

        self.registry = get_registry()

    def refs(self, master="m1"):
        from action_platform.core.flow.remote import RemoteRefs

        return RemoteRefs(
            branches={"main": master, "feature/7-x": "f1"},
            tags={"v1.0.0": "t1"},
            default_branch="main",
        )

    def host(self):
        from action_platform.core.context import CommitRow, TagRow
        from action_platform.providers.source.github import SourceGithub

        files = {"platform.toml": TOML, "LAST_VERSION": "1.0.0\n"}
        stamp = datetime(2026, 11, 27, 10)

        return mock.patch.multiple(
            SourceGithub,
            file=mock.Mock(side_effect=lambda repo, ref, path: files.get(path)),
            tags=mock.Mock(
                return_value=[
                    TagRow(
                        name="v1.0.0",
                        sha="t1abcdef",
                        date=stamp,
                        subject="chore(release): 1.0.0",
                    )
                ]
            ),
            commits=mock.Mock(
                return_value=[
                    CommitRow(
                        sha="m1abcdef", subject="feat: x", author="Ada", date=stamp
                    )
                ]
            ),
            compare=mock.Mock(return_value=[]),
        )

    def sync(self, refs):
        from app.schemas import SourceCredentials
        from app.services.projects.apps.service import AppService

        with mock.patch(
            "app.services.projects.apps.inventory.remote_refs", return_value=refs
        ):
            return AppService(self.registry).sync(
                self.registry_id, SourceCredentials(kind="github", token="ghp")
            )

    def test_sync_builds_the_snapshot_from_the_host_without_cloning(self):
        from action_platform.core.flow.repository import Repository
        from app.repositories.workspace.snapshots import SnapshotStore

        with (
            self.host(),
            mock.patch.object(
                Repository, "clone", side_effect=AssertionError("sync cloned")
            ),
            mock.patch(
                "app.services.workspace.checkout.Workspaces.refresh",
                side_effect=AssertionError("sync refreshed the clone"),
            ),
        ):
            self.sync(self.refs())

        data, _ = SnapshotStore(self.app.state.db).get(self.registry_id)

        self.assertEqual(data["detail"]["project"]["name"], "demo")
        self.assertEqual(data["detail"]["last_version"], "1.0.0")
        self.assertEqual(data["detail"]["latest_tag"], "v1.0.0")
        self.assertEqual(data["tags"], ["v1.0.0"])
        self.assertEqual(data["releases"][0]["date"], "2026-11-27")
        self.assertEqual(
            data["commits"][0],
            {
                "sha": "m1abcde",
                "subject": "feat: x",
                "author": "Ada",
                "date": "2026-11-27",
            },
        )
        self.assertEqual({b["name"] for b in data["branches"]}, {"main", "feature/7-x"})
        self.assertTrue(data["manifest"]["mirrored"])

        res = self.client.get(
            f"/api/v1/apps/{self.registry_id}/releases", headers=self.h()
        )
        self.assertEqual(res.status_code, 200, res.text)

    def test_unchanged_refs_skip_the_host(self):
        from action_platform.providers.source.github import SourceGithub

        with self.host():
            self.sync(self.refs())
            SourceGithub.file.reset_mock()
            self.sync(self.refs())
            self.assertFalse(SourceGithub.file.called)

            self.sync(self.refs(master="m2"))
            self.assertTrue(SourceGithub.file.called)

    def test_a_draft_lays_over_the_host_file(self):
        from app.repositories.workspace.snapshots import SnapshotStore

        self.registry.drafts.replace(self.registry_id, {"LAST_VERSION": "2.0.0\n"})

        with self.host():
            self.sync(self.refs())

        data, _ = SnapshotStore(self.app.state.db).get(self.registry_id)

        self.assertEqual(data["detail"]["last_version"], "2.0.0")
        self.assertFalse(data["detail"]["clean"])

    def test_a_host_that_cannot_read_falls_back_to_the_clone(self):
        from app.schemas import SourceCredentials
        from app.services.projects.apps.service import AppService

        with (
            mock.patch(
                "app.services.projects.apps.inventory.remote_refs",
                side_effect=AssertionError("asked the remote"),
            ),
            mock.patch("app.services.workspace.checkout.Workspaces.refresh") as refresh,
            mock.patch("app.services.projects.apps.inventory.AppInventory._snapshot"),
        ):
            entry = self.registry.get(self.registry_id)
            refresh.return_value = (entry, Path(entry.path))
            AppService(self.registry).sync(
                self.registry_id,
                SourceCredentials(
                    kind="generic", token="t", base_url="https://git.acme.io"
                ),
            )

        self.assertTrue(refresh.called)

    def test_a_host_error_falls_back_to_the_clone(self):
        from action_platform.core.exception import ProviderError
        from action_platform.providers.source.github import SourceGithub

        with (
            self.host(),
            mock.patch.object(
                SourceGithub, "tags", side_effect=ProviderError("graphql down")
            ),
            mock.patch("app.services.workspace.checkout.Workspaces.refresh") as refresh,
            mock.patch("app.services.projects.apps.inventory.AppInventory._snapshot"),
        ):
            entry = self.registry.get(self.registry_id)
            refresh.return_value = (entry, Path(entry.path))
            self.sync(self.refs())

        self.assertTrue(refresh.called)
