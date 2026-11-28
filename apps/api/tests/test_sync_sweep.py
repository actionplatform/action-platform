"""The scheduled sync: due apps get a sync job, sooner the more recently they changed."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta

from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


class IntervalTest(unittest.TestCase):
    def test_recent_changes_sync_sooner(self):
        from app.services.projects.sync_sweep import interval

        at = datetime(2026, 11, 28, 12)

        self.assertEqual(interval(at - timedelta(minutes=5), at), timedelta(minutes=2))
        self.assertEqual(interval(at - timedelta(hours=5), at), timedelta(minutes=10))
        self.assertEqual(interval(at - timedelta(days=3), at), timedelta(hours=1))
        self.assertEqual(interval(at - timedelta(days=30), at), timedelta(hours=6))
        self.assertEqual(interval(None, at), timedelta(hours=1))


@unittest.skipUnless(TestClient, "fastapi is not installed")
class SyncSweepTest(GateCase):
    def sweep(self):
        from app.services.jobs import JobQueue
        from app.services.projects.sync_sweep import SyncSweep

        db = self.app.state.db

        return SyncSweep(db, JobQueue(db))

    def test_a_due_app_gets_one_sync_and_waits_its_turn(self):
        from sqlalchemy import select

        from app.core.db.models import App, Job
        from app.core.shared.clock import now

        self.register()

        self.assertEqual(self.sweep().run(), {"apps": 1})
        self.assertEqual(self.sweep().run(), {"apps": 0})

        with self.app.state.db.session() as s:
            jobs = s.scalars(select(Job).where(Job.kind == "sync")).all()
            app = s.get(App, "a1")

            self.assertEqual(len(jobs), 1)
            self.assertTrue(json.loads(jobs[0].payload)["scheduled"])
            self.assertGreater(
                app.next_sync_at, now() + timedelta(minutes=55)
            )
            self.assertEqual(
                len(
                    s.scalars(
                        select(Job).where(
                            Job.kind == "sync_sweep", Job.status == "queued"
                        )
                    ).all()
                ),
                1,
            )

    def test_a_change_makes_the_app_hot(self):
        from app.core.db.models import App

        self.register()
        self.sweep().changed("a1")

        with self.app.state.db.session() as s:
            app = s.get(App, "a1")

            self.assertIsNotNone(app.last_change_at)
            self.assertLessEqual(
                app.next_sync_at - app.last_change_at, timedelta(minutes=2)
            )
