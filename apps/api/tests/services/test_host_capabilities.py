"""What the API does with a code host that lacks a capability: it asks the host's protocols instead of catching NotImplementedError."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from action_platform.providers.source.github import SourceGithub
from action_platform.core.exception import ActionPlatformError
from app.core.errors import Conflict
from app.core.shared.credentials import Credentials
from app.schemas import SourceCredentials
from app.services.activity.imports.service import ActivityService
from app.services.projects.apps.remote import AppRemote


def creds(kind: str) -> Credentials:
    return Credentials(
        kind=kind,
        token="t",
        username=None,
        base_url="https://git.acme.io",
        owner=None,
    )


class ActivityCapabilityTest(unittest.TestCase):
    def test_a_plain_git_server_has_no_releases_or_pull_requests(self):
        service = ActivityService(db=None)

        self.assertEqual(service.remote_releases(creds("generic"), "acme/x"), [])
        self.assertEqual(service.remote_pull_requests(creds("generic"), "acme/x"), [])

    def test_an_unknown_kind_has_nothing_to_import(self):
        service = ActivityService(db=None)

        self.assertEqual(service.remote_releases(creds("svn"), "acme/x"), [])

    def test_a_host_that_lists_them_is_asked(self):
        service = ActivityService(db=None)

        with (
            mock.patch.object(SourceGithub, "releases", return_value=["r"]),
            mock.patch.object(SourceGithub, "pull_requests", return_value=["p"]),
        ):
            self.assertEqual(service.remote_releases(creds("github"), "acme/x"), ["r"])
            self.assertEqual(
                service.remote_pull_requests(creds("github"), "acme/x"), ["p"]
            )


class DeleteRepositoryCapabilityTest(unittest.TestCase):
    def test_a_host_that_cannot_delete_is_a_conflict(self):
        remote = AppRemote.__new__(AppRemote)

        with mock.patch.object(
            AppRemote, "repository_of", return_value=("generic", "acme/x")
        ):
            with self.assertRaises(Conflict) as raised:
                remote.delete_repository(
                    "app", SourceCredentials(kind="generic", token="t")
                )

        self.assertIn("generic cannot delete repositories", str(raised.exception))


class RepositoryOfTest(unittest.TestCase):
    def remote(self, entry):
        remote = AppRemote.__new__(AppRemote)
        remote.registry = mock.Mock()
        remote.registry.get.return_value = entry
        remote.configs = mock.Mock()
        remote.workspace = mock.Mock(side_effect=AssertionError("cloned"))

        return remote

    def test_a_missing_clone_is_not_created_to_find_the_repository(self):
        entry = SimpleNamespace(
            url="https://github.com/acme/x.git", path="/nonexistent/clone"
        )

        self.assertEqual(self.remote(entry).repository_of("app"), ("github", "acme/x"))

    def test_an_app_without_a_url_has_no_repository(self):
        entry = SimpleNamespace(url="", path="/nonexistent/clone")

        self.assertIsNone(self.remote(entry).repository_of("app"))

    def test_a_failed_lookup_is_not_swallowed(self):
        remote = AppRemote.__new__(AppRemote)

        with mock.patch.object(
            AppRemote, "repository_of", side_effect=ActionPlatformError("boom")
        ):
            with self.assertRaises(ActionPlatformError):
                remote.delete_through_host(
                    mock.Mock(), "org", SimpleNamespace(registry_id="app")
                )

    def test_an_app_without_a_remote_is_skipped(self):
        remote = AppRemote.__new__(AppRemote)

        with mock.patch.object(AppRemote, "repository_of", return_value=None):
            self.assertIsNone(
                remote.delete_through_host(
                    mock.Mock(), "org", SimpleNamespace(registry_id="app")
                )
            )
