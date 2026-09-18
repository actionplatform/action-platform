"""Server-side pages: releases, pull requests, CI runs and jobs answer with items, total, page and per."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from action_platform.core.context import Run
from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient, "fastapi is not installed")
class PagesTest(GateCase):
    def setUp(self):
        super().setUp()
        self.registry_id = self.register()

    def test_releases_page(self):
        from app.repositories.releases import ReleaseStore

        with self.app.state.db.session() as s:
            for i in range(23):
                ReleaseStore(s).ensure(
                    "a1",
                    f"v1.0.{i}",
                    "git",
                    published_at=datetime(2026, 1, 1 + i % 28, tzinfo=timezone.utc),
                )

        base = "/api/v1/projects/p1/apps/a1/releases"
        first = self.client.get(f"{base}?page=1&per=10", headers=self.h()).json()
        self.assertEqual(
            (first["total"], first["page"], first["per"], len(first["items"])),
            (23, 1, 10, 10),
        )
        last = self.client.get(f"{base}?page=3&per=10", headers=self.h()).json()
        self.assertEqual(len(last["items"]), 3)
        self.assertNotEqual(first["items"][0]["tag"], last["items"][0]["tag"])
        clamped = self.client.get(f"{base}?page=0&per=1000", headers=self.h()).json()
        self.assertEqual((clamped["page"], clamped["per"]), (1, 100))

    def test_pull_requests_page(self):
        from app.core.db.models import PullRequest

        with self.app.state.db.session() as s:
            for i in range(12):
                s.add(
                    PullRequest(
                        id=f"pr{i}",
                        app_id="a1",
                        number=i + 1,
                        title=f"PR {i}",
                        url="https://x",
                        head=f"feature/{i}",
                        base="develop",
                        state="open",
                        draft=False,
                        created_at=datetime(2026, 1, 1, i),
                        updated_at=datetime(2026, 1, 1, i),
                        source="github",
                    )
                )

        body = self.client.get(
            "/api/v1/projects/p1/apps/a1/pull-requests?page=2&per=10", headers=self.h()
        ).json()
        self.assertEqual((body["total"], body["page"], len(body["items"])), (12, 2, 2))
        self.assertEqual(body["items"][0]["number"], 2)

    def test_ci_runs_page(self):
        from unittest import mock

        from app.core.db.models import App, SourceHost

        with self.app.state.db.session() as s:
            s.add(
                SourceHost(
                    id="h1",
                    organization_id=self.org["id"],
                    kind="github",
                    name="GitHub",
                    auth_kind="token",
                    token_encrypted=self.app.state.sealer.seal("ghp"),
                )
            )
            s.get(App, "a1").source_host_id = "h1"

        runs = [Run(number=n, status="success", branch="main") for n in range(1, 16)]
        with mock.patch(
            "action_platform.providers.ci.github_actions.CIGithubActions.runs",
            return_value=runs,
        ):
            body = self.client.post(
                "/api/v1/projects/p1/apps/a1/ci/sync?per=5", headers=self.h()
            ).json()

        self.assertEqual(
            (body["total"], body["page"], body["per"], len(body["runs"])), (15, 1, 5, 5)
        )
        self.assertEqual(body["runs"][0]["number"], 15)
        page3 = self.client.get(
            "/api/v1/projects/p1/apps/a1/ci?page=3&per=5", headers=self.h()
        ).json()
        self.assertEqual([r["number"] for r in page3["runs"]], [5, 4, 3, 2, 1])

    def test_jobs_page(self):
        from app.services.jobs import JobQueue

        queue = JobQueue(self.app.state.db)
        for i in range(7):
            queue.enqueue(
                "deploy" if i % 2 else "destroy",
                {"body": {"stage": "dev"}},
                organization_id=self.org["id"],
                app_id="a1",
            )
        queue.enqueue("sync", {}, organization_id=self.org["id"], app_id="a1")

        body = self.client.get(
            f"/api/v1/jobs/page?app={self.registry_id}&per=5", headers=self.h()
        ).json()
        self.assertEqual((body["total"], body["page"], len(body["items"])), (7, 1, 5))
        only = self.client.get(
            f"/api/v1/jobs/page?app={self.registry_id}&kinds=deploy&per=10",
            headers=self.h(),
        ).json()
        self.assertEqual(only["total"], 3)
