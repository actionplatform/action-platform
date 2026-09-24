"""app.services.activity.imports — typed rows from the code host land in the release and pull_request tables."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest import mock

from action_platform.core.context import PullRequestRow, ReleaseRow
from action_platform.providers.source.github import SourceGithub
from app.core.shared.credentials import Credentials
from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

RELEASE = ReleaseRow(
    tag="v1.2.0",
    name="Release 1.2.0",
    body="notes",
    url="https://gh/r/1",
    author="ada",
    sha=None,
    prerelease=False,
    draft=False,
    published_at=datetime(2026, 9, 17, 10),
    source="github",
)

PULL = PullRequestRow(
    number=7,
    title="Add x",
    url="https://gh/p/7",
    author="ada",
    head="feature/7",
    base="develop",
    state="merged",
    draft=False,
    created_at=datetime(2026, 9, 17, 9),
    updated_at=datetime(2026, 9, 17, 11),
    merged_at=datetime(2026, 9, 17, 11),
    source="github",
)

CREDS = Credentials(kind="github", token="t", username=None, base_url=None, owner=None)


@unittest.skipUnless(TestClient, "fastapi is not installed")
class ActivityImportTest(GateCase):
    def setUp(self):
        super().setUp()
        self.register()

    def test_releases_and_pull_requests_are_stored_from_typed_rows(self):
        from app.core.db.models import PullRequest
        from app.repositories.releases import ReleaseStore
        from app.services.activity import ActivityService

        with (
            mock.patch.object(SourceGithub, "releases", return_value=[RELEASE]),
            mock.patch.object(SourceGithub, "pull_requests", return_value=[PULL]),
            self.app.state.db.session() as s,
        ):
            errors = ActivityService(s).sync_all("a1", CREDS, "acme/x")
            release = ReleaseStore(s).get("a1", "v1.2.0")
            pull = s.query(PullRequest).filter_by(app_id="a1").one()

            self.assertEqual(errors, {"releases": None, "pull_requests": None})
            self.assertEqual(
                (release.source, release.name, release.author, release.url),
                ("github", "Release 1.2.0", "ada", "https://gh/r/1"),
            )
            self.assertEqual(
                (pull.number, pull.state, pull.head, pull.base, pull.source),
                (7, "merged", "feature/7", "develop", "github"),
            )
