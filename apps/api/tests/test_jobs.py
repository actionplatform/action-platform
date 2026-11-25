"""The job queue and the worker: enqueue, claim, retry, dedupe; async routes answer 202 and the worker runs them."""

from __future__ import annotations

import unittest
from unittest import mock

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

    def test_a_job_its_worker_still_holds_is_not_reaped(self):
        from datetime import timedelta

        from app.core.db.models import Job
        from app.core.shared.clock import now

        queue = self.queue()
        job = queue.enqueue("deploy", {})
        queue.claim("w")

        with queue.database.session() as s:
            s.query(Job).filter(Job.id == job.id).update(
                {"locked_at": now() - timedelta(hours=1)}
            )

        queue.touch(job.id, "other")
        queue.touch(job.id, "w")

        self.assertEqual(queue.reap(), 0)
        self.assertEqual(queue.get(job.id).status, "running")

    def test_the_worker_keeps_the_lock_fresh_while_a_job_runs(self):
        from unittest import mock

        from app.services.jobs import worker as module

        touched = []
        holder = mock.Mock()
        holder.name = "w"
        holder.queue.touch.side_effect = lambda id, name: touched.append((id, name))

        with mock.patch.object(module, "HEARTBEAT_SECONDS", 0.01):
            with module.Worker.holding(holder, "job-1"):
                import time

                time.sleep(0.1)

        self.assertIn(("job-1", "w"), touched)
        count = len(touched)
        time.sleep(0.05)
        self.assertEqual(len(touched), count)


class AsyncRouteTest(GateCase):
    def test_sync_with_prefer_async_is_queued_and_the_worker_runs_it(self):
        from app.services.jobs.worker import Worker

        registry_id = self.register()
        res = self.client.post(
            f"/api/v1/apps/{registry_id}/sync",
            json={},
            headers=self.h(),
        )
        self.assertEqual(res.status_code, 202, res.text)
        job_id = res.json()["job"]
        seen = self.client.get(f"/api/v1/jobs/{job_id}", headers=self.h()).json()
        self.assertEqual((seen["status"], seen["kind"]), ("queued", "sync"))
        again = self.client.post(
            f"/api/v1/apps/{registry_id}/sync",
            json={},
            headers=self.h(),
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

    def test_a_token_queues_a_job_on_sqlite(self):
        registry_id = self.register()
        headers = {
            **self.h(self.token("read,write")),
            "X-Action-Platform-Client": "Claude Code/1",
        }

        res = self.client.post(
            f"/api/v1/apps/{registry_id}/sync", json={}, headers=headers
        )

        self.assertEqual(res.status_code, 202, res.text)

    def test_what_the_worker_writes_can_be_followed_line_by_line(self):
        from action_platform.logging import emit, logger
        from app.services.jobs import registry
        from app.services.jobs.worker import Worker

        registry_id = self.register()
        res = self.client.post(
            f"/api/v1/apps/{registry_id}/sync",
            json={},
            headers=self.h(),
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
            {
                "lines": [],
                "next": 99,
                "status": "done",
                "kind": "sync",
                "no_worker": False,
                "finished": True,
            },
        )

    def test_a_deploy_job_carries_the_app_and_the_plugin_options(self):
        from app.services.deployments import DeployEnv
        from app.services.jobs.context import JobContext
        from app.services.integrations.plugins.options import DbOptions

        registry_id = self.register()
        DbOptions(self.app.state.db, "aws-lambda", self.org["id"]).set(
            "proxy_url", "https://p.test"
        )

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

    def test_a_deploy_job_signs_tokens_about_its_app_and_stage_without_scopes(
        self,
    ):
        import json
        from base64 import urlsafe_b64decode
        from app.core.db.models import Job
        from app.services.deployments.identity import AppIdentity
        from app.services.jobs.context import JobContext

        registry_id = self.register()

        self.scopes("dev", "prod")
        res = self.client.post(
            f"/api/v1/apps/{registry_id}/deploy",
            json={"stage": "dev", "dry_run": False},
            headers=self.h(),
        )

        self.assertEqual(res.status_code, 202, res.text)
        with self.app.state.db.session() as db:
            payload = json.loads(db.get(Job, res.json()["job"]).payload)

        self.assertNotIn("manages", payload)

        ctx = JobContext.of(payload, self.app.state.db, self.app.state.sealer)
        mint = AppIdentity(
            self.app.state.db, self.app.state.sealer, "https://ap.test"
        ).minter(ctx.organization, ctx.app, "dev")
        claims = json.loads(
            urlsafe_b64decode(mint("sts.amazonaws.com").split(".")[1] + "==")
        )

        self.assertNotIn("scopes", claims)
        self.assertEqual(claims["stage"], "dev")

    def test_a_body_beyond_the_limit_is_refused_before_anything_runs(self):
        from app.api.gate import MAX_BODY

        res = self.client.post(
            "/api/v1/apps",
            content=b"{" + b" " * (MAX_BODY + 1) + b"}",
            headers={**self.h(), "content-type": "application/json"},
        )

        self.assertEqual(res.status_code, 413)

    def test_a_sync_is_a_job_the_worker_runs(self):
        from app.services.jobs.worker import Worker

        registry_id = self.register()

        res = self.client.post(
            f"/api/v1/apps/{registry_id}/sync", json={}, headers=self.h()
        )

        self.assertEqual(res.status_code, 202, res.text)
        Worker(self.app.state.db, self.app.state.secrets, "test").run(
            once=True, kinds=["sync"]
        )
        jobs = {
            j["kind"]: j["status"]
            for j in self.client.get(
                "/api/v1/jobs", params={"app": registry_id}, headers=self.h()
            ).json()
        }
        self.assertEqual(jobs, {"sync": "done"})

    def test_a_queued_deploy_lists_with_its_stage_and_who_asked(self):
        registry_id = self.register()
        self.scopes("dev", "prod")
        res = self.client.post(
            f"/api/v1/apps/{registry_id}/deploy",
            json={"stage": "prod", "dry_run": False},
            headers=self.h(),
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
            ("prod", False, "Ana"),
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
        self.scopes("dev", "prod")
        headers = self.h()
        first = self.client.post(
            f"/api/v1/apps/{registry_id}/deploy",
            json={"stage": "dev", "dry_run": False},
            headers=headers,
        )
        again = self.client.post(
            f"/api/v1/apps/{registry_id}/deploy",
            json={"stage": "dev", "dry_run": False},
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


class ShippingDeployTest(GateCase):
    def setUp(self):
        super().setUp()
        from app.repositories.configuration.config_store import ConfigStore

        self.registry_id = self.register()
        self.scopes("dev", "prod")
        ConfigStore(self.app.state.db).set(
            self.registry_id,
            {
                "project": {"name": "demo"},
                "deploy": {
                    "targets": [
                        {"name": "lambda", "kind": "aws/lambda", "stages": ["dev"]}
                    ]
                },
            },
        )

    def deployments(self) -> list[tuple]:
        from app.core.db.models import Deployment

        with self.app.state.db.session() as s:
            return [
                (d.target, d.stage, d.version, d.status, d.executor, d.job_id, d.actor)
                for d in s.query(Deployment).all()
            ]

    def work(self, seen: list) -> None:
        """Run the queued deploy with the real handler; the deploy itself only notes the deployment rows that already exist."""
        from app.services.deployments import DeploymentsService
        from app.services.jobs.worker import Worker

        def deploy(service, id, request):
            seen.extend(self.deployments())

            return [
                {
                    "target": "lambda",
                    "ok": True,
                    "version": "1.2.3",
                    "url": None,
                    "error": None,
                    "stage": "dev",
                }
            ]

        with mock.patch.object(DeploymentsService, "deploy", deploy):
            Worker(self.app.state.db, self.app.state.secrets, "test").run(once=True)

    def test_a_deploy_is_always_a_job(self):
        res = self.client.post(
            f"/api/v1/apps/{self.registry_id}/deploy",
            json={"stage": "dev", "version": "1.2.3", "dry_run": False},
            headers=self.h(),
        )

        self.assertEqual(res.status_code, 202, res.text)
        queued = res.json()
        self.assertEqual(
            (queued["status"], queued["poll"]),
            ("queued", f"/api/v1/jobs/{queued['job']}"),
        )
        jobs = self.client.get(
            "/api/v1/jobs/page",
            params={"app": self.registry_id},
            headers=self.h(),
        ).json()["items"]
        self.assertEqual(
            [
                (j["id"], j["kind"], j["dry_run"], j["stage"], j["version"], j["by"])
                for j in jobs
            ],
            [(queued["job"], "deploy", False, "dev", "1.2.3", "Ana")],
        )

    def test_sync_push_and_release_are_always_jobs(self):
        for path, body in (
            ("sync", {}),
            ("push", {}),
            ("release", {"level": "patch", "dry_run": False}),
        ):
            with self.subTest(path=path):
                res = self.client.post(
                    f"/api/v1/apps/{self.registry_id}/{path}",
                    json=body,
                    headers=self.h(),
                )

                self.assertEqual(res.status_code, 202, res.text)
                self.assertEqual(res.json()["status"], "queued")

    def test_dry_run_is_read_as_the_request_model_reads_it(self):
        from app.core.errors import Invalid
        from app.services.access.job_dispatcher import dry_run

        for value in (False, 0, 0.0, "false", "off", "no", "f", "n", "0"):
            with self.subTest(value=value):
                self.assertFalse(dry_run({"dry_run": value}))

        for value in (True, 1, "true", "on", "yes"):
            with self.subTest(value=value):
                self.assertTrue(dry_run({"dry_run": value}))

        self.assertTrue(dry_run({}))

        with self.assertRaises(Invalid):
            dry_run({"dry_run": "maybe"})

    def test_a_deploy_spelled_off_is_a_job_and_nonsense_is_refused(self):
        from app.services.jobs import JobQueue

        off = self.client.post(
            f"/api/v1/apps/{self.registry_id}/deploy",
            json={"stage": "dev", "version": "1.2.3", "dry_run": "off"},
            headers=self.h(),
        )
        nonsense = self.client.post(
            f"/api/v1/apps/{self.registry_id}/deploy",
            json={"stage": "prod", "version": "1.2.3", "dry_run": "maybe"},
            headers=self.h(),
        )

        self.assertEqual(off.status_code, 202, off.text)
        self.assertEqual(nonsense.status_code, 400, nonsense.text)
        self.assertEqual(
            [j.id for j in JobQueue(self.app.state.db).for_app("a1")],
            [off.json()["job"]],
        )

    def test_a_dry_run_answers_inline_and_leaves_no_job(self):
        from app.services.jobs import JobQueue

        with mock.patch(
            "app.services.deployments.DeploymentsService.deploy",
            lambda service, id, request: [
                {"target": "lambda", "ok": True, "version": "1.2.3", "stage": "dev"}
            ],
        ):
            res = self.client.post(
                f"/api/v1/apps/{self.registry_id}/deploy",
                json={"stage": "dev", "version": "1.2.3", "dry_run": True},
                headers=self.h(),
            )

        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual([r["target"] for r in res.json()], ["lambda"])
        self.assertEqual(JobQueue(self.app.state.db).for_app("a1"), [])

    def test_the_worker_records_the_deployment_before_it_follows_the_run(self):
        res = self.client.post(
            f"/api/v1/apps/{self.registry_id}/deploy",
            json={"stage": "dev", "version": "1.2.3", "dry_run": False},
            headers=self.h(),
        )
        job_id = res.json()["job"]
        seen: list = []

        self.work(seen)

        self.assertEqual(
            seen, [("lambda", "dev", "1.2.3", "running", "platform", job_id, "Ana")]
        )
        self.assertEqual(
            self.deployments(),
            [("lambda", "dev", "1.2.3", "success", "platform", job_id, "Ana")],
        )

    def test_a_deploy_that_raises_leaves_its_row_failed(self):
        from app.services.deployments import DeploymentsService
        from app.services.jobs import JobQueue
        from app.services.jobs.worker import Worker

        res = self.client.post(
            f"/api/v1/apps/{self.registry_id}/deploy",
            json={"stage": "dev", "version": "1.2.3", "dry_run": False},
            headers=self.h(),
        )
        self.assertEqual(res.status_code, 202, res.text)

        def deploy(service, id, request):
            raise RuntimeError("connection reset")

        with mock.patch.object(DeploymentsService, "deploy", deploy):
            Worker(self.app.state.db, self.app.state.secrets, "test").run(once=True)

        job = JobQueue(self.app.state.db).get(res.json()["job"])
        self.assertEqual(job.status, "queued")
        self.assertEqual(
            [(d[3], d[4], d[5]) for d in self.deployments()],
            [("failure", "platform", job.id)],
        )

    def test_a_deploy_without_a_version_records_the_release_at_head(self):
        from app.services.deployments import DeploymentsService
        from app.services.jobs.worker import Worker

        res = self.client.post(
            f"/api/v1/apps/{self.registry_id}/deploy",
            json={"stage": "dev", "dry_run": False},
            headers=self.h(),
        )
        seen: list = []

        def deploy(service, id, request):
            seen.extend(self.deployments())
            raise RuntimeError("connection reset")

        with mock.patch.object(DeploymentsService, "deploy", deploy):
            Worker(self.app.state.db, self.app.state.secrets, "test").run(once=True)

        job_id = res.json()["job"]
        self.assertEqual(
            seen, [("lambda", "dev", "1.2.3", "running", "platform", job_id, "Ana")]
        )
        self.assertEqual(
            [(d[2], d[3]) for d in self.deployments()], [("1.2.3", "failure")]
        )


class ConcurrentWorkerTest(GateCase):
    def test_several_jobs_run_at_once_and_kinds_filter_what_is_taken(self):
        import threading
        import time

        from app.services.jobs import JobQueue
        from app.services.jobs.worker import Worker

        self.register()
        queue = JobQueue(self.app.state.db)
        for n in range(4):
            queue.enqueue("slow", {}, organization_id=self.org["id"], app_id=f"a{n}")
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


class AppLockTest(TempCase):
    def database(self):
        from app.core.db import Database

        db = Database(f"sqlite:///{self.tmp_path / 'l.db'}")
        db.migrate()

        return db

    def test_one_holder_per_app(self):
        from app.services.jobs.locks import AppLocks

        locks = AppLocks(self.database())

        with locks.hold("a1") as first:
            with locks.hold("a1") as second, locks.hold("a2") as other:
                self.assertEqual((first, second, other), (True, False, True))

            with locks.hold(None) as appless:
                self.assertTrue(appless)

        with locks.hold("a1") as again:
            self.assertTrue(again)

    def test_a_deferred_job_keeps_its_attempts(self):
        from datetime import timedelta

        from app.services.jobs import JobQueue

        queue = JobQueue(self.database())
        job = queue.enqueue("readiness", {}, app_id="a1")
        queue.claim("w")
        queue.defer(job.id, "w", timedelta(0))
        back = queue.get(job.id)

        self.assertEqual(
            (back.status, back.attempts, back.locked_by), ("queued", 0, None)
        )
        self.assertEqual(queue.claim("w").attempts, 1)


class AppSerialWorkerTest(GateCase):
    def test_jobs_of_one_app_take_turns_while_other_apps_run_alongside(self):
        import threading
        import time
        from datetime import timedelta

        from app.core.db.models import Job
        from app.services.jobs import JobQueue
        from app.services.jobs.worker import Worker

        self.register()
        queue = JobQueue(self.app.state.db)

        for app_id in ("a1", "a1", "a1", "a2", "a2"):
            queue.enqueue(
                "readiness",
                {"app": app_id},
                organization_id=self.org["id"],
                app_id=app_id,
            )

        guard = threading.Lock()
        running: dict[str, int] = {"a1": 0, "a2": 0, "all": 0}
        peak: dict[str, int] = {"a1": 0, "a2": 0, "all": 0}

        def readiness(payload):
            app_id = payload["app"]

            with guard:
                for key in (app_id, "all"):
                    running[key] += 1
                    peak[key] = max(peak[key], running[key])
            time.sleep(0.2)
            with guard:
                for key in (app_id, "all"):
                    running[key] -= 1

            return {"ok": True}

        worker = Worker(self.app.state.db, self.app.state.secrets, "test")
        worker.handlers = {"readiness": readiness}
        defer = worker.queue.defer
        worker.queue.defer = lambda id, name: defer(id, name, timedelta(0))

        deadline = time.monotonic() + 10

        while time.monotonic() < deadline:
            worker.run(once=True, concurrency=3, kinds=["readiness"])

            with self.app.state.db.session() as s:
                if s.query(Job).filter(Job.status != "done").count() == 0:
                    break

        with self.app.state.db.session() as s:
            jobs = s.query(Job).filter_by(kind="readiness").all()

        self.assertEqual({(j.status, j.attempts) for j in jobs}, {("done", 1)})
        self.assertEqual((peak["a1"], peak["a2"]), (1, 1))
        self.assertEqual(peak["all"], 2)


class PersonLabelTest(unittest.TestCase):
    def test_name_first_email_when_there_is_none(self):
        from types import SimpleNamespace

        from app.core.shared import people

        self.assertEqual(people.label(SimpleNamespace(name="Ana", email="a@x")), "Ana")
        self.assertEqual(people.label(SimpleNamespace(name="  ", email="a@x")), "a@x")
        self.assertIsNone(people.label(None))
