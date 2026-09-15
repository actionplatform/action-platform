"""The job queue and the worker: enqueue, claim, retry, dedupe; async routes answer 202 and the worker runs them."""

from __future__ import annotations

from tests.api.test_access import GateCase
from tests.support import TempCase


class QueueTest(TempCase):
    def queue(self):
        from action_platform.api.db import Database
        from action_platform.api.services.jobs import JobQueue

        db = Database(f"sqlite:///{self.tmp_path / 'q.db'}")
        db.migrate()

        return JobQueue(db)

    def test_enqueue_claim_finish(self):
        queue = self.queue()
        job = queue.enqueue(
            "sync", {"registry_id": "r1"}, app_id="a1", dedupe_key="sync"
        )
        self.assertEqual(
            queue.enqueue("sync", {}, app_id="a1", dedupe_key="sync").id, job.id
        )
        claimed = queue.claim("w1")
        self.assertEqual(
            (claimed.id, claimed.status, claimed.attempts, claimed.locked_by),
            (job.id, "running", 1, "w1"),
        )
        self.assertIsNone(queue.claim("w2"))
        queue.finish(job.id, {"ok": True})
        done = queue.get(job.id)
        self.assertEqual((done.status, done.result), ("done", '{"ok": true}'))
        self.assertNotEqual(
            queue.enqueue("sync", {}, app_id="a1", dedupe_key="sync").id, job.id
        )

    def test_fail_retries_with_backoff_then_gives_up(self):
        from action_platform.api.services.jobs import MAX_ATTEMPTS
        from action_platform.api.services.shared.clock import now

        queue = self.queue()
        job = queue.enqueue("release", {})

        for attempt in range(1, MAX_ATTEMPTS + 1):
            with queue.database.session() as s:
                from action_platform.api.db.models import Job

                s.query(Job).filter(Job.id == job.id).update({"run_after": now()})
            claimed = queue.claim("w")
            self.assertEqual(claimed.attempts, attempt)
            queue.fail(job.id, "boom")

        final = queue.get(job.id)
        self.assertEqual((final.status, final.error), ("failed", "boom"))

    def test_refused_jobs_do_not_retry(self):
        queue = self.queue()
        job = queue.enqueue("deploy", {})
        queue.claim("w")
        queue.fail(job.id, "nope", retry=False)
        self.assertEqual(queue.get(job.id).status, "failed")

    def test_stale_running_jobs_are_reaped(self):
        from datetime import timedelta

        from action_platform.api.db.models import Job
        from action_platform.api.services.shared.clock import now

        queue = self.queue()
        job = queue.enqueue("sync", {})
        queue.claim("w")

        with queue.database.session() as s:
            s.query(Job).filter(Job.id == job.id).update(
                {"locked_at": now() - timedelta(hours=1)}
            )

        self.assertEqual(queue.reap(), 1)
        self.assertEqual(queue.get(job.id).status, "queued")


class AsyncRouteTest(GateCase):
    def test_sync_with_prefer_async_is_queued_and_the_worker_runs_it(self):
        from action_platform.api.worker import Worker

        registry_id = self.register()
        res = self.client.post(
            f"/api/v1/apps/{registry_id}/sync",
            json={},
            headers={**self.h(), "Prefer": "respond-async"},
        )
        self.assertEqual(res.status_code, 202, res.text)
        job_id = res.json()["job"]
        seen = self.client.get(f"/api/v1/jobs/{job_id}", headers=self.h()).json()
        self.assertEqual((seen["status"], seen["kind"]), ("queued", "sync"))
        again = self.client.post(
            f"/api/v1/apps/{registry_id}/sync",
            json={},
            headers={**self.h(), "Prefer": "respond-async"},
        )
        self.assertEqual(again.json()["job"], job_id)

        worker = Worker(self.app.state.db, self.app.state.secrets, "test")
        self.assertEqual(worker.run(once=True), 1)

        done = self.client.get(f"/api/v1/jobs/{job_id}", headers=self.h()).json()
        self.assertEqual(done["status"], "done", done)
        self.assertEqual(done["result"]["id"], registry_id)
        listed = self.client.get(
            "/api/v1/jobs", params={"app": registry_id}, headers=self.h()
        ).json()
        self.assertEqual([j["id"] for j in listed], [job_id])

    def test_jobs_of_another_organization_are_invisible(self):
        from action_platform.api.services.jobs import JobQueue

        job = JobQueue(self.app.state.db).enqueue("sync", {}, organization_id="other")
        self.assertEqual(
            self.client.get(f"/api/v1/jobs/{job.id}", headers=self.h()).status_code, 404
        )

    def test_workspace_is_rebuilt_on_a_fresh_instance(self):
        import shutil
        from pathlib import Path

        from action_platform.api.core.deps import get_registry

        registry_id = self.register()
        entry = get_registry().get(registry_id)
        shutil.rmtree(Path(entry.path))
        res = self.client.get(f"/api/v1/apps/{registry_id}", headers=self.h())
        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue((Path(entry.path) / "platform.toml").exists())


class RegistryAdoptionTest(GateCase):
    def test_entries_from_apps_json_are_adopted_into_the_database(self):
        import json
        from pathlib import Path

        from action_platform.api.core.deps import configure_registry, get_registry
        from action_platform.api.repositories.registry import home

        file = home() / "apps.json"
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(
            json.dumps(
                [
                    {
                        "id": "01old",
                        "name": "legacy",
                        "url": self.url,
                        "path": str(home() / "workspaces" / "01old"),
                        "default_branch": "main",
                    }
                ]
            )
        )
        configure_registry(self.app.state.db)
        entry = get_registry().get("01old")
        self.assertEqual((entry.name, entry.url), ("legacy", self.url))
        self.assertTrue(Path(entry.path).name == "01old")
        self.assertFalse(file.exists())
        self.assertTrue(file.with_suffix(".json.imported").exists())
        self.assertEqual(get_registry().adopt_file(), [])
