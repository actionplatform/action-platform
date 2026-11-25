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

    def test_app_activity_lists_every_kind_newest_first(self):
        self.register()
        self.seed()

        body = self.client.get(
            "/api/v1/projects/p1/apps/a1/activity", headers=self.h()
        ).json()

        kinds = [e["kind"] for e in body["events"]]
        self.assertEqual(kinds[0], "ci_run")
        self.assertEqual(
            set(kinds), {"ci_run", "deployment", "release", "pull_request"}
        )
        self.assertEqual(len(kinds), 8)
        self.assertTrue(all(e["app_id"] == "a1" for e in body["events"]))

    def test_app_activity_filters_one_kind(self):
        self.register()
        self.seed()

        body = self.client.get(
            "/api/v1/projects/p1/apps/a1/activity?kind=release", headers=self.h()
        ).json()

        self.assertEqual([e["title"] for e in body["events"]], ["v1.1.0", "v1.0.0"])

        limited = self.client.get(
            "/api/v1/projects/p1/apps/a1/activity?kind=pull_request&limit=1",
            headers=self.h(),
        ).json()

        self.assertEqual([e["title"] for e in limited["events"]], ["#2 New"])

    def test_app_activity_refuses_an_unknown_kind_and_app(self):
        self.register()

        self.assertEqual(
            self.client.get(
                "/api/v1/projects/p1/apps/a1/activity?kind=audit", headers=self.h()
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.get(
                "/api/v1/projects/p1/apps/nope/activity", headers=self.h()
            ).status_code,
            404,
        )

    def test_latest_events_follow_the_event_time_not_the_sync(self):
        from app.core.db.models import Deployment
        from app.core.shared.clock import now

        self.register()
        moment = now()
        with self.app.state.db.session() as s:
            for i in range(13):
                s.add(
                    Deployment(
                        id=f"old{i}",
                        app_id="a1",
                        target="lambda",
                        kind="aws/lambda",
                        stage="prod",
                        version=f"0.{i}.0",
                        status="success",
                        executor="jenkins",
                        external_ref=f"jenkins:{i}",
                        started_at=moment - timedelta(days=30, minutes=i),
                        finished_at=moment - timedelta(days=30, minutes=i),
                        synced_at=moment,
                    )
                )
            s.add(
                Deployment(
                    id="fresh",
                    app_id="a1",
                    target="lambda",
                    kind="aws/lambda",
                    stage="prod",
                    version="2.0.0",
                    status="success",
                    executor="jenkins",
                    external_ref="jenkins:99",
                    started_at=moment - timedelta(minutes=5),
                    finished_at=moment - timedelta(minutes=2),
                    synced_at=moment - timedelta(hours=1),
                )
            )

        body = self.client.get("/api/v1/dashboard?fresh=true", headers=self.h()).json()

        self.assertEqual(body["events"][0]["title"], "lambda 2.0.0")

    def test_in_progress_lists_active_deployments_and_skips_the_cache(self):
        from app.core.db.models import Deployment
        from app.core.shared.clock import now

        self.register()
        self.seed()
        self.client.get("/api/v1/dashboard", headers=self.h())
        moment = now()
        with self.app.state.db.session() as s:
            for ref, status, started in (
                ("r1", "running", moment - timedelta(minutes=2)),
                ("r2", "queued", None),
                ("r3", "running", moment - timedelta(seconds=30)),
                ("r4", "failure", moment - timedelta(seconds=10)),
            ):
                s.add(
                    Deployment(
                        id=ref,
                        app_id="a1",
                        target="lambda",
                        kind="aws/lambda",
                        stage="prod",
                        version="1.2.0",
                        status=status,
                        executor="jenkins",
                        external_ref=f"jenkins:{ref}",
                        started_at=started,
                    )
                )

        body = self.client.get("/api/v1/dashboard", headers=self.h()).json()

        self.assertEqual([d["id"] for d in body["in_progress"]], ["r3", "r1", "r2"])
        first = body["in_progress"][0]
        self.assertEqual(first["app"], "demo")
        self.assertEqual(first["project_id"], "p1")
        self.assertEqual(first["stage"], "prod")
        self.assertEqual(first["status"], "running")
        self.assertIsNone(body["in_progress"][2]["started_at"])

        with self.app.state.db.session() as s:
            s.get(Deployment, "r3").status = "success"

        body = self.client.get("/api/v1/dashboard", headers=self.h()).json()

        self.assertEqual([d["id"] for d in body["in_progress"]], ["r1", "r2"])

    def test_in_progress_is_empty_without_active_deployments(self):
        self.register()
        self.seed()

        body = self.client.get("/api/v1/dashboard?fresh=true", headers=self.h()).json()

        self.assertEqual(body["in_progress"], [])
