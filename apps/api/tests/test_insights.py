"""Insights: the organization's dashboard and a release's timeline."""

from __future__ import annotations

import unittest
from datetime import timedelta

from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient, "fastapi is not installed")
class InsightsTest(GateCase):
    def seed(self):
        from app.core.db.models import CiRun, Deployment, PullRequest
        from app.core.shared.clock import now
        from app.repositories import insights
        from app.repositories.releases import ReleaseStore

        moment = now().replace(hour=12, minute=0, second=0, microsecond=0)
        self.patch(insights, "now", lambda: moment)
        with self.app.state.db.session() as s:
            store = ReleaseStore(s)
            old = store.ensure(
                "a1", "v1.0.0", "git", published_at=moment - timedelta(days=10)
            )
            new = store.ensure(
                "a1",
                "v1.1.0",
                "platform",
                name="Release 1.1.0",
                published_at=moment - timedelta(hours=2),
            )
            s.add(
                PullRequest(
                    id="pr1",
                    app_id="a1",
                    number=1,
                    title="Old",
                    url="u",
                    head="feature/1",
                    base="main",
                    state="merged",
                    draft=False,
                    created_at=moment - timedelta(days=12),
                    updated_at=moment - timedelta(days=11),
                    merged_at=moment - timedelta(days=11),
                    source="github",
                )
            )
            s.add(
                PullRequest(
                    id="pr2",
                    app_id="a1",
                    number=2,
                    title="New",
                    url="u",
                    head="feature/2",
                    base="main",
                    state="merged",
                    draft=False,
                    created_at=moment - timedelta(days=3),
                    updated_at=moment - timedelta(days=3),
                    merged_at=moment - timedelta(days=3),
                    source="github",
                )
            )
            s.add(
                CiRun(
                    id="c1",
                    app_id="a1",
                    source="github_actions",
                    number=10,
                    status="success",
                    branch="v1.1.0",
                    started_at=moment - timedelta(hours=1),
                )
            )
            s.add(
                CiRun(
                    id="c2",
                    app_id="a1",
                    source="github_actions",
                    number=11,
                    status="failure",
                    branch="main",
                    started_at=moment - timedelta(minutes=30),
                )
            )
            s.add(
                Deployment(
                    id="d1",
                    app_id="a1",
                    target="lambda",
                    kind="aws/lambda",
                    stage="prod",
                    version="1.1.0",
                    release_id=new.id,
                    status="verified",
                    executor="platform",
                    external_ref="job-1",
                    started_at=moment - timedelta(minutes=50),
                    finished_at=moment - timedelta(minutes=45),
                )
            )
            s.add(
                Deployment(
                    id="d0",
                    app_id="a1",
                    target="lambda",
                    kind="aws/lambda",
                    stage="prod",
                    version="1.0.0",
                    release_id=old.id,
                    status="success",
                    executor="platform",
                    external_ref="job-0",
                    started_at=moment - timedelta(days=9),
                    finished_at=moment - timedelta(days=9),
                )
            )

    def test_dashboard_counts_the_day_and_lists_events(self):
        self.register()
        self.seed()

        body = self.client.get("/api/v1/dashboard", headers=self.h()).json()

        self.assertEqual(body["apps"], 1)
        self.assertEqual(body["deployments_today"], {"verified": 1})
        self.assertEqual(body["ci_today"], {"success": 1, "failure": 1})
        self.assertEqual(body["releases_week"], 1)
        self.assertEqual([a["app"] for a in body["without_ci"]], ["demo"])
        kinds = [e["kind"] for e in body["events"]]
        self.assertIn("deployment", kinds)
        self.assertIn("release", kinds)
        self.assertIn("ci_run", kinds)
        self.assertEqual(body["events"][0]["kind"], "ci_run")

    def test_timeline_stitches_what_shipped_the_release(self):
        self.register()
        self.seed()

        body = self.client.get(
            "/api/v1/projects/p1/apps/a1/releases/v1.1.0/timeline", headers=self.h()
        ).json()

        self.assertEqual(body["release"]["tag"], "v1.1.0")
        self.assertEqual(body["previous"]["tag"], "v1.0.0")
        self.assertEqual([p["number"] for p in body["pull_requests"]], [2])
        self.assertEqual([c["number"] for c in body["ci_runs"]], [10])
        self.assertEqual([d["version"] for d in body["deployments"]], ["1.1.0"])

        self.assertEqual(
            self.client.get(
                "/api/v1/projects/p1/apps/a1/releases/v9.9.9/timeline", headers=self.h()
            ).status_code,
            404,
        )
