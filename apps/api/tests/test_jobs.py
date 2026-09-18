"""The job queue and the worker: enqueue, claim, retry, dedupe; async routes answer 202 and the worker runs them."""

from __future__ import annotations

import unittest

from action_platform.testing.fixtures import TempCase
from tests.test_access import GateCase


class QueueTest(TempCase):
    def queue(self):
        from app.core.db import Database
        from app.services.jobs import JobQueue

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
        from app.core.shared.clock import now
        from app.services.jobs import MAX_ATTEMPTS

        queue = self.queue()
        job = queue.enqueue("release", {})

        for attempt in range(1, MAX_ATTEMPTS + 1):
            with queue.database.session() as s:
                from app.core.db.models import Job

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

        from app.core.db.models import Job
        from app.core.shared.clock import now

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
        from app.services.jobs.worker import Worker

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

    def test_what_the_worker_writes_can_be_followed_line_by_line(self):
        from action_platform.logging import emit, logger
        from app.services.jobs import registry
        from app.services.jobs.worker import Worker

        registry_id = self.register()
        res = self.client.post(
            f"/api/v1/apps/{registry_id}/sync",
            json={},
            headers={**self.h(), "Prefer": "respond-async"},
        )
        job_id = res.json()["job"]

        def chatty(payload):
            logger.info("deploy target=%s", "fake")
            emit("$ sam build")
            emit("Build Succeeded")

            return {"ok": True}

        original = registry._factories["sync"]
        registry.register("sync", lambda s: chatty)

        try:
            Worker(self.app.state.db, self.app.state.secrets, "test").run(once=True)
        finally:
            registry.register("sync", original)

        first = self.client.get(
            f"/api/v1/jobs/{job_id}/logs", params={"limit": 2}, headers=self.h()
        ).json()
        rest = self.client.get(
            f"/api/v1/jobs/{job_id}/logs",
            params={"after": first["next"]},
            headers=self.h(),
        ).json()
        lines = [row["line"] for row in first["lines"] + rest["lines"]]

        self.assertEqual(first["next"], 2)
        self.assertIn("deploy target=fake", lines)
        self.assertEqual(
            lines[-3:], ["$ sam build", "Build Succeeded", f"job sync {job_id} done"]
        )
        self.assertTrue(rest["finished"])
        self.assertEqual(rest["status"], "done")
        self.assertEqual(
            self.client.get(
                f"/api/v1/jobs/{job_id}/logs", params={"after": 99}, headers=self.h()
            ).json(),
            {"lines": [], "next": 99, "status": "done", "finished": True},
        )

    def test_a_deploy_job_carries_the_app_and_the_plugin_options(self):
        from app.services.deployments import DeployEnv
        from app.services.jobs.context import JobContext
        from app.services.integrations.plugins.options import DbOptions

        registry_id = self.register()
        DbOptions(self.app.state.db, "aws-lambda").set("proxy_url", "https://p.test")

        ctx = JobContext.of(
            {
                "registry_id": registry_id,
                "organization_id": self.org["id"],
                "app_id": "a1",
                "path": f"apps/{registry_id}/deploy",
                "body": {},
            },
            self.app.state.db,
            self.app.state.sealer,
        )

        env = DeployEnv(self.app.state.db).for_app(ctx.organization, ctx.app)

        self.assertEqual(env["AP_AWS_LAMBDA_PROXY_URL"], "https://p.test")
        self.assertEqual(env["AP_APP"], f"{ctx.organization.slug}/web/demo")

    def test_a_deploy_queued_by_an_org_manager_signs_tokens_that_may_register_the_app(
        self,
    ):
        import json
        from base64 import urlsafe_b64decode
        from app.core.db.models import Job
        from app.services.deployments.identity import AppIdentity
        from app.services.jobs.context import JobContext

        registry_id = self.register()
        res = self.client.post(
            f"/api/v1/apps/{registry_id}/deploy",
            json={"stage": "dev", "dry_run": True},
            headers={**self.h(), "Prefer": "respond-async"},
        )

        self.assertEqual(res.status_code, 202, res.text)
        with self.app.state.db.session() as db:
            payload = json.loads(db.get(Job, res.json()["job"]).payload)

        self.assertTrue(payload["manages"])

        ctx = JobContext.of(payload, self.app.state.db, self.app.state.sealer)
        mint = AppIdentity(
            self.app.state.db, self.app.state.sealer, "https://ap.test"
        ).minter(ctx.organization, ctx.app, "dev", manages=payload["manages"])
        claims = json.loads(
            urlsafe_b64decode(mint("https://proxy.test").split(".")[1] + "==")
        )

        self.assertEqual(claims["scopes"], ["org.manage"])
        self.assertEqual(claims["stage"], "dev")

    def test_a_body_beyond_the_limit_is_refused_before_anything_runs(self):
        from app.api.gate import MAX_BODY

        res = self.client.post(
            "/api/v1/apps",
            content=b"{" + b" " * (MAX_BODY + 1) + b"}",
            headers={**self.h(), "content-type": "application/json"},
        )

        self.assertEqual(res.status_code, 413)

    def test_an_inline_sync_leaves_the_host_import_to_the_worker(self):
        registry_id = self.register()

        res = self.client.post(
            f"/api/v1/apps/{registry_id}/sync", json={}, headers=self.h()
        )

        self.assertEqual(res.status_code, 200, res.text)
        kinds = [
            j["kind"]
            for j in self.client.get(
                "/api/v1/jobs", params={"app": registry_id}, headers=self.h()
            ).json()
        ]
        self.assertIn("import", kinds)

    def test_a_queued_deploy_lists_with_its_stage_and_who_asked(self):
        registry_id = self.register()
        res = self.client.post(
            f"/api/v1/apps/{registry_id}/deploy",
            json={"stage": "prod", "dry_run": True},
            headers={**self.h(), "X-Async": "1"},
        )
        self.assertEqual(res.status_code, 202, res.text)

        deploys = self.client.get(
            "/api/v1/jobs",
            params={"app": registry_id, "kind": "deploy"},
            headers=self.h(),
        ).json()
        syncs = self.client.get(
            "/api/v1/jobs",
            params={"app": registry_id, "kind": "sync"},
            headers=self.h(),
        ).json()

        self.assertEqual(len(deploys), 1)
        self.assertEqual(
            (deploys[0]["stage"], deploys[0]["dry_run"], deploys[0]["by"]),
            ("prod", True, "Ana"),
        )
        self.assertEqual(syncs, [])

    def test_jobs_of_another_organization_are_invisible(self):
        from app.services.jobs import JobQueue

        job = JobQueue(self.app.state.db).enqueue("sync", {}, organization_id="other")
        self.assertEqual(
            self.client.get(f"/api/v1/jobs/{job.id}", headers=self.h()).status_code, 404
        )

    def test_workspace_is_rebuilt_on_a_fresh_instance(self):
        import shutil
        from pathlib import Path

        from app.repositories.workspace.source import get_registry

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

        from app.repositories.workspace.registry import home
        from app.repositories.workspace.source import (
            configure_registry,
            get_registry,
        )

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

    def test_deleting_an_app_with_cloud_cleanup_tears_the_stacks_down_then_removes_it(
        self,
    ):
        from unittest import mock

        from app.core.db.models import App
        from app.services.deployments import DeploymentsService
        from app.services.jobs.worker import Worker

        registry_id = self.register()
        res = self.client.delete(
            "/api/v1/projects/p1/apps/a1", params={"cloud": 1}, headers=self.h()
        )

        self.assertEqual(res.status_code, 202, res.text)
        job_id = res.json()["job"]

        with self.app.state.db.session() as s:
            self.assertIsNotNone(s.get(App, "a1"))

        torn: list[tuple[str, tuple[str, ...]]] = []

        def destroy(self_, id, stages=("dev", "prod")):
            torn.append((id, stages))

        with mock.patch.object(DeploymentsService, "destroy", destroy):
            worker = Worker(self.app.state.db, self.app.state.secrets, "test")
            self.assertEqual(worker.run(once=True), 1)

        done = self.client.get(f"/api/v1/jobs/{job_id}", headers=self.h()).json()

        self.assertEqual(done["status"], "done", done)
        self.assertEqual(torn, [(registry_id, ("dev", "prod"))])
        self.assertEqual(done["result"]["removed"], [registry_id])

        with self.app.state.db.session() as s:
            self.assertIsNone(s.get(App, "a1"))

    def test_one_deploy_at_a_time_per_environment(self):
        registry_id = self.register()
        headers = {**self.h(), "Prefer": "respond-async"}
        first = self.client.post(
            f"/api/v1/apps/{registry_id}/deploy",
            json={"stage": "dev", "dry_run": False},
            headers=headers,
        )
        again = self.client.post(
            f"/api/v1/apps/{registry_id}/deploy",
            json={"stage": "dev", "dry_run": True},
            headers=headers,
        )
        other = self.client.post(
            f"/api/v1/apps/{registry_id}/deploy",
            json={"stage": "prod", "dry_run": False},
            headers=headers,
        )

        self.assertEqual(first.status_code, 202, first.text)
        self.assertEqual(again.status_code, 409, again.text)
        self.assertIn("already queued", again.json()["detail"])
        self.assertEqual(other.status_code, 202, other.text)

    def test_deleting_a_project_with_cloud_cleanup_tears_every_app_down_then_removes_it(
        self,
    ):
        from unittest import mock

        from app.core.db.models import App, Project
        from app.services.deployments import DeploymentsService
        from app.services.jobs.worker import Worker

        registry_id = self.register()
        res = self.client.delete(
            "/api/v1/projects/p1", params={"cloud": 1}, headers=self.h()
        )

        self.assertEqual(res.status_code, 202, res.text)
        torn: list[str] = []

        def destroy(self_, id, stages=("dev", "prod")):
            torn.append(id)

        with mock.patch.object(DeploymentsService, "destroy", destroy):
            self.assertEqual(
                Worker(self.app.state.db, self.app.state.secrets, "test").run(
                    once=True
                ),
                1,
            )

        done = self.client.get(
            f"/api/v1/jobs/{res.json()['job']}", headers=self.h()
        ).json()

        self.assertEqual(done["status"], "done", done)
        self.assertEqual(torn, [registry_id])

        with self.app.state.db.session() as s:
            self.assertIsNone(s.get(App, "a1"))
            self.assertIsNone(s.get(Project, "p1"))


class ConcurrentWorkerTest(GateCase):
    def test_several_jobs_run_at_once_and_kinds_filter_what_is_taken(self):
        import threading
        import time

        from app.services.jobs import JobQueue
        from app.services.jobs.worker import Worker

        self.register()
        queue = JobQueue(self.app.state.db)
        for _ in range(4):
            queue.enqueue("slow", {}, organization_id=self.org["id"], app_id="a1")
        queue.enqueue("other", {}, organization_id=self.org["id"], app_id="a1")

        peak = {"now": 0, "max": 0}
        lock = threading.Lock()

        def slow(payload):
            with lock:
                peak["now"] += 1
                peak["max"] = max(peak["max"], peak["now"])
            time.sleep(0.3)
            with lock:
                peak["now"] -= 1
            return {"ok": True}

        worker = Worker(self.app.state.db, self.app.state.secrets, "test")
        worker.handlers = {"slow": slow, "other": lambda payload: {"ok": True}}

        started = time.monotonic()
        done = worker.run(once=True, concurrency=4, kinds=["slow"])
        elapsed = time.monotonic() - started

        self.assertEqual(done, 4)
        self.assertGreaterEqual(peak["max"], 2)
        self.assertLess(elapsed, 1.0)
        with self.app.state.db.session() as s:
            from app.core.db.models import Job

            self.assertEqual(
                {j.status for j in s.query(Job).filter_by(kind="slow")}, {"done"}
            )
            self.assertEqual(
                s.query(Job).filter_by(kind="other").one().status, "queued"
            )


class PersonLabelTest(unittest.TestCase):
    def test_name_first_email_when_there_is_none(self):
        from types import SimpleNamespace

        from app.core.shared import people

        self.assertEqual(people.label(SimpleNamespace(name="Ana", email="a@x")), "Ana")
        self.assertEqual(people.label(SimpleNamespace(name="  ", email="a@x")), "a@x")
        self.assertIsNone(people.label(None))
