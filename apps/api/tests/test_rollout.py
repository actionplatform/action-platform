"""Deployments run step by step: the plan stored when the deploy starts, one job per step, waits rescheduled instead of slept, and the controls between steps."""

from __future__ import annotations

import unittest
from datetime import timedelta

from action_platform.core.rollout import OperationResult
from action_platform.testing.operations import MockOperations, MockTarget
from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

BASE = "/api/v1/projects/p1/apps/a1"


class Flaky(MockOperations):
    """deploy_new is called, then the worker dies before the answer is stored."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.crashes = 1

    def deploy_new(self, ctx):
        found = super().deploy_new(ctx)

        if self.crashes:
            self.crashes -= 1
            raise RuntimeError("worker lost")

        return found


@unittest.skipUnless(TestClient, "fastapi is not installed")
class RolloutCase(GateCase):
    def setUp(self):
        super().setUp()
        from app.repositories.configuration.config_store import ConfigStore

        self.registry_id = self.register()
        self.scopes("dev")
        ConfigStore(self.app.state.db).set(
            self.registry_id,
            {
                "project": {"name": "demo"},
                "deploy": {"targets": [{"name": "mock", "kind": "mock"}]},
            },
        )
        self.ops: MockOperations | None = MockOperations()
        self.target = MockTarget()
        self.patch(
            "action_platform.core.module.load_deploy_targets",
            value=lambda: {"mock": self.build},
        )

    def build(self, **options):
        self.target.ops = self.ops

        return self.target

    def deploy(self, **body):
        return self.client.post(
            f"{BASE}/deploy",
            json={"stage": "dev", "version": "1.2.3", "dry_run": False, **body},
            headers=self.h(),
        )

    def work(self) -> None:
        from app.services.jobs.worker import Worker

        Worker(self.app.state.db, self.app.state.secrets, "test").run(once=True)

    def due(self) -> None:
        """Every wait over and every queued job due — time passes without anyone sleeping."""
        from app.core.db.models import DeploymentStep, Job
        from app.core.shared.clock import now

        past = now() - timedelta(seconds=1)

        with self.app.state.db.session() as s:
            for step in s.query(DeploymentStep).filter(
                DeploymentStep.not_before.is_not(None)
            ):
                step.not_before = past

            for job in s.query(Job).filter(Job.status == "queued"):
                job.run_after = past

    def deployment(self) -> dict:
        rows = self.client.get(f"{BASE}/deployments", headers=self.h()).json()
        self.assertEqual(len(rows["deployments"]), 1, rows)

        return rows["deployments"][0]

    def steps(self, id: str) -> list[tuple[str, str]]:
        res = self.client.get(f"{BASE}/deployments/{id}/steps", headers=self.h())
        self.assertEqual(res.status_code, 200, res.text)

        return [(s["kind"], s["status"]) for s in res.json()]

    def control(self, id: str, action: str):
        return self.client.post(f"{BASE}/deployments/{id}/{action}", headers=self.h())

    def queued_steps(self) -> list:
        from app.core.db.models import Job

        with self.app.state.db.session() as s:
            return [
                j.run_after
                for j in s.query(Job).filter(
                    Job.kind == "deploy_step", Job.status == "queued"
                )
            ]


class CatalogTest(RolloutCase):
    def test_every_strategy_with_its_schema_and_the_safety_schema(self):
        res = self.client.get("/api/v1/deploy-strategies", headers=self.h())

        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(
            [s["id"] for s in body["strategies"]],
            ["recreate", "rolling", "blue_green", "canary", "shadow"],
        )
        canary = body["strategies"][3]
        self.assertEqual(
            canary["needs"], ["deploy_new", "shift", "health", "retire_old"]
        )
        self.assertEqual(
            canary["config_schema"]["properties"]["steps"]["default"][0],
            {"weight": 5, "pause_seconds": 300},
        )
        self.assertEqual(
            body["safety_schema"]["properties"]["auto_rollback"]["default"], True
        )

    def test_a_scope_lists_what_its_targets_support(self):
        self.ops = MockOperations({"deploy_new", "shift", "retire_old", "health"})

        res = self.client.get(f"{BASE}/scopes/dev/strategies", headers=self.h())

        self.assertEqual(res.status_code, 200, res.text)
        found = {s["id"]: s for s in res.json()}
        self.assertTrue(found["recreate"]["supported"])
        self.assertTrue(found["canary"]["supported"])
        self.assertFalse(found["shadow"]["supported"])
        self.assertIn("mirror", found["shadow"]["reason"])
        self.assertEqual(found["rolling"]["missing"], ["replace"])
        self.assertEqual(
            self.client.get(
                f"{BASE}/scopes/nope/strategies", headers=self.h()
            ).status_code,
            404,
        )


class RecreateTest(RolloutCase):
    def test_the_default_deploy_is_todays_deploy(self):
        self.ops = None

        res = self.deploy()
        self.assertEqual(res.status_code, 202, res.text)
        self.work()

        row = self.deployment()
        self.assertEqual((row["status"], row["strategy"]), ("success", "recreate"))
        self.assertEqual(self.target.deployed, ["1.2.3"])
        self.assertEqual(self.steps(row["id"]), [])
        self.assertEqual(self.queued_steps(), [])

    def test_recreate_with_approval_waits_then_deploys_through_the_target(self):
        self.ops = None

        self.deploy(safety={"manual_approval": True})
        self.work()
        row = self.deployment()

        self.assertEqual(row["status"], "awaiting_approval")
        self.assertEqual(self.target.deployed, [])

        self.assertEqual(self.control(row["id"], "promote").status_code, 202)
        self.work()

        self.assertEqual(self.deployment()["status"], "success")
        self.assertEqual(self.target.deployed, ["1.2.3"])
        self.assertEqual(
            self.steps(row["id"]),
            [
                ("approval", "succeeded"),
                ("deploy_new", "succeeded"),
                ("retire_old", "skipped"),
            ],
        )


class ValidationTest(RolloutCase):
    def test_an_unknown_strategy_or_a_bad_config_is_refused_before_a_job(self):
        for body in (
            {"strategy": "teleport"},
            {"strategy": "rolling", "strategy_config": {"batch_percent": 0}},
            {"strategy": "canary", "safety": {"manual_approval": "yes"}},
        ):
            with self.subTest(body=body):
                res = self.deploy(**body)

                self.assertEqual(res.status_code, 400, res.text)

    def test_a_strategy_the_target_cannot_run_fails_naming_the_missing_operations(self):
        from app.core.db.models import Job

        self.ops = None

        self.assertEqual(self.deploy(strategy="canary").status_code, 202)
        self.work()

        with self.app.state.db.session() as s:
            job = s.query(Job).filter(Job.kind == "deploy").one()
            self.assertEqual(job.status, "failed")
            self.assertIn("deploy_new", job.error)

        self.assertEqual(self.deployment()["status"], "failure")
        self.assertEqual(self.target.deployed, [])


class CanaryTest(RolloutCase):
    CONFIG = {
        "steps": [
            {"weight": 50, "pause_seconds": 60},
            {"weight": 100, "pause_seconds": 0},
        ]
    }

    def test_steps_run_in_order_and_a_pause_is_rescheduled_not_slept(self):
        from app.core.shared.clock import now

        self.assertEqual(
            self.deploy(strategy="canary", strategy_config=self.CONFIG).status_code, 202
        )
        self.work()
        row = self.deployment()

        self.assertEqual(row["status"], "running")
        self.assertEqual(row["operations"], sorted(self.ops.supports()))
        self.assertEqual(
            self.steps(row["id"]),
            [
                ("deploy_new", "succeeded"),
                ("shift", "succeeded"),
                ("pause", "waiting"),
                ("health", "pending"),
                ("shift", "pending"),
                ("health", "pending"),
                ("retire_old", "pending"),
            ],
        )
        self.assertEqual(self.ops.called(), ["deploy_new", "shift"])
        due = self.queued_steps()
        self.assertEqual(len(due), 1)
        self.assertGreater(due[0], now() + timedelta(seconds=50))

        self.due()
        self.work()

        self.assertEqual(self.deployment()["status"], "success")
        self.assertEqual(
            self.ops.called(),
            ["deploy_new", "shift", "health", "shift", "health", "retire_old"],
        )
        self.assertEqual(
            [p.get("weight") for op, p in self.ops.calls if op == "shift"], [50, 100]
        )

    def test_a_deploy_to_the_scope_waits_while_one_is_paused(self):
        self.deploy(strategy="canary", strategy_config=self.CONFIG)
        self.work()
        row = self.deployment()

        self.assertEqual(self.control(row["id"], "pause").status_code, 200)
        again = self.deploy()

        self.assertEqual(again.status_code, 409, again.text)
        self.assertIn("paused", again.text)

    def test_pause_holds_the_plan_and_resume_continues(self):
        self.deploy(strategy="canary", strategy_config=self.CONFIG)
        self.work()
        row = self.deployment()

        paused = self.control(row["id"], "pause")
        self.assertEqual(paused.status_code, 200, paused.text)
        self.assertEqual(paused.json()["deployment"]["status"], "paused")
        self.due()
        self.work()

        self.assertEqual(self.ops.called(), ["deploy_new", "shift"])
        self.assertEqual(self.control(row["id"], "pause").status_code, 409)

        self.assertEqual(self.control(row["id"], "resume").status_code, 202)
        self.due()
        self.work()

        self.assertEqual(self.deployment()["status"], "success")

    def test_promote_skips_the_current_wait(self):
        self.deploy(strategy="canary", strategy_config=self.CONFIG)
        self.work()
        row = self.deployment()

        res = self.control(row["id"], "promote")
        self.assertEqual(res.status_code, 202, res.text)
        self.work()

        self.assertEqual(self.deployment()["status"], "success")
        self.assertEqual(self.steps(row["id"])[2], ("pause", "skipped"))


class ApprovalTest(RolloutCase):
    def test_manual_approval_waits_and_promote_continues(self):
        self.deploy(
            strategy="blue_green",
            strategy_config={"bake_seconds": 0},
            safety={"manual_approval": True},
        )
        self.work()
        row = self.deployment()

        self.assertEqual(row["status"], "awaiting_approval")
        self.assertEqual(self.ops.called(), ["deploy_new", "health"])
        self.assertEqual(self.queued_steps(), [])
        self.assertEqual(self.deploy().status_code, 409)

        res = self.control(row["id"], "promote")
        self.assertEqual(res.status_code, 202, res.text)
        self.assertTrue(res.json()["queued"])
        self.work()

        self.assertEqual(self.deployment()["status"], "success")
        self.assertEqual(
            self.ops.called(), ["deploy_new", "health", "shift", "retire_old"]
        )
        events = self.client.get(
            f"{BASE}/deployments/{row['id']}/events", headers=self.h()
        ).json()
        self.assertIn(("approved", "Ana"), [(e["kind"], e["actor"]) for e in events])

    def test_promote_with_nothing_waiting_is_refused(self):
        self.deploy(strategy="blue_green", strategy_config={"bake_seconds": 0})
        self.work()
        row = self.deployment()

        self.assertEqual(row["status"], "success")
        self.assertEqual(self.control(row["id"], "promote").status_code, 409)
        self.assertEqual(self.control("nope", "promote").status_code, 404)


class RollbackTest(RolloutCase):
    CONFIG = {"steps": [{"weight": 100, "pause_seconds": 0}]}

    def test_a_failed_health_check_rolls_back(self):
        self.ops.answer("health", OperationResult(False, "5xx above threshold"))

        self.deploy(strategy="canary", strategy_config=self.CONFIG)
        self.work()
        row = self.deployment()

        self.assertEqual(row["status"], "rolled_back")
        self.assertIn("5xx", row["error"])
        self.assertEqual(
            self.ops.called(), ["deploy_new", "shift", "health", "rollback"]
        )
        self.assertEqual(
            self.steps(row["id"]),
            [
                ("deploy_new", "succeeded"),
                ("shift", "succeeded"),
                ("health", "failed"),
                ("retire_old", "cancelled"),
                ("rollback", "succeeded"),
            ],
        )

    def test_without_auto_rollback_a_failed_health_check_fails(self):
        self.ops.answer("health", OperationResult(False, "5xx"))

        self.deploy(
            strategy="canary",
            strategy_config=self.CONFIG,
            safety={"auto_rollback": False},
        )
        self.work()

        self.assertEqual(self.deployment()["status"], "failure")
        self.assertNotIn("rollback", self.ops.called())


class AbortTest(RolloutCase):
    def awaiting(self) -> str:
        self.deploy(
            strategy="blue_green",
            strategy_config={"bake_seconds": 0},
            safety={"manual_approval": True},
        )
        self.work()
        row = self.deployment()
        self.assertEqual(row["status"], "awaiting_approval")

        return row["id"]

    def test_abort_rolls_back_when_the_target_can(self):
        id = self.awaiting()

        res = self.control(id, "abort")
        self.assertEqual(res.status_code, 202, res.text)
        self.assertEqual(res.json()["deployment"]["status"], "rolling_back")
        self.work()

        self.assertEqual(self.deployment()["status"], "aborted")
        self.assertEqual(self.ops.called(), ["deploy_new", "health", "rollback"])
        self.assertEqual(self.control(id, "abort").status_code, 409)

    def test_abort_without_rollback_stops_and_says_what_is_live(self):
        self.ops = MockOperations({"deploy_new", "health", "shift", "retire_old"})
        id = self.awaiting()

        res = self.control(id, "abort")

        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["deployment"]["status"], "aborted")
        self.assertIn("serves no traffic", res.json()["live"])
        self.assertEqual(self.queued_steps(), [])


class RestartTest(RolloutCase):
    def test_a_step_whose_worker_died_is_asked_for_its_status_not_called_again(self):
        self.ops = Flaky()
        self.ops.answer("status", OperationResult(True, data={"state": "succeeded"}))

        self.deploy(strategy="blue_green", strategy_config={"bake_seconds": 0})
        self.work()
        row = self.deployment()

        self.assertEqual(row["status"], "running")
        self.assertEqual(self.steps(row["id"])[0], ("deploy_new", "running"))

        self.due()
        self.work()

        self.assertEqual(self.deployment()["status"], "success")
        self.assertEqual(self.ops.called("deploy_new"), ["deploy_new"])
        self.assertEqual(
            self.ops.called(),
            ["deploy_new", "status", "health", "shift", "retire_old"],
        )

    def test_a_status_that_knows_nothing_calls_the_operation_again(self):
        self.ops = Flaky()
        self.ops.answer("status", OperationResult(False, "unknown"))

        self.deploy(strategy="blue_green", strategy_config={"bake_seconds": 0})
        self.work()
        self.due()
        self.work()

        self.assertEqual(self.deployment()["status"], "success")
        self.assertEqual(self.ops.called("deploy_new"), ["deploy_new", "deploy_new"])


class NativeTest(RolloutCase):
    def test_a_native_strategy_is_started_once_and_followed_with_status(self):
        self.ops = MockOperations({"status", "rollback"}, native={"canary"})
        self.ops.answer(
            "status",
            OperationResult(True, data={"state": "running"}),
            OperationResult(True, "done", data={"state": "succeeded"}),
        )

        self.deploy(strategy="canary")
        self.work()
        row = self.deployment()

        self.assertEqual(self.steps(row["id"]), [("native", "running")])
        self.assertEqual(self.ops.called(), ["native"])

        self.due()
        self.work()
        self.assertEqual(self.deployment()["status"], "running")
        self.due()
        self.work()

        self.assertEqual(self.deployment()["status"], "success")
        self.assertEqual(self.ops.called(), ["native", "status", "status"])
        self.assertEqual(self.ops.calls[0][1]["strategy"], "canary")
