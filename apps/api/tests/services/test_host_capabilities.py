"""What the API does with a code host that lacks a capability: it asks the host's protocols instead of catching NotImplementedError."""

from __future__ import annotations

import unittest
from unittest import mock

from action_platform.providers.source.github import SourceGithub
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
