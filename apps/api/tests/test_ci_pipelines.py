"""App › CI › Pipelines: every job of an app read live through the CIRunner contract — runs, stages, logs, tests, artifacts — and the organization's queue and executors."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from typing import Iterator
from unittest import mock

from action_platform.abc.ci_runner import (
    Artifact,
    CIRunner,
    Executor,
    LogChunk,
    PendingInput,
    QueueItem,
    Stage,
    TestFailure,
    TestReport,
)
from action_platform.core.context import Cause, Change, Run
from action_platform.core.exception import ProviderError
from app.services.ci.pipelines import MAX_LOG_BYTES, capped
from app.services.ci.redact import redact
from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

CI_JOB = "team/demo/main"
CD_JOB = "team/demo-deploy"
LOG = "Started by user ana\n\x1b[32mok\x1b[0m\ntoken ghp_abcdefghijklmnopqrstuvwxyz0123456789\n"


class FakeRunner(CIRunner):
    name = "jenkins"

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.log_size = len(LOG.encode())

    def runs(self, job: str, limit: int = 50) -> list[Run]:
        self.calls.append(("runs", job))

        if job == CI_JOB:
            return [
                Run(
                    number=8,
                    status="running",
                    branch="main",
                    started_at=datetime(2026, 11, 26, 10, tzinfo=timezone.utc),
                ),
                Run(
                    number=7,
                    status="failure",
                    branch="main",
                    started_at=datetime(2026, 11, 25, 10, tzinfo=timezone.utc),
                ),
            ]

        return [
            Run(
                number=3,
                status="success",
                trigger="platform deploy",
                started_at=datetime(2026, 11, 25, 12, tzinfo=timezone.utc),
            )
        ]

    def run(self, job: str, number: int) -> Run:
        return Run(
            number=number,
            status="running" if number == 8 else "failure",
            branch="main",
            sha="abc1234",
            params={"STAGE": "dev", "TOKEN": "glpat-abcdefghijklmnopqrstu"},
            causes=[Cause("Started by GitHub push", "ana")],
            changes=[Change("abc1234", "ana", "feat: x")],
        )

    def stages(self, job: str, number: int) -> list[Stage]:
        return [
            Stage(id="1", name="Build", status="success", duration_ms=1000),
            Stage(id="2", name="Test", status="running"),
            Stage(id="3", name="unit", status="success", parent_id="2"),
            Stage(id="4", name="e2e", status="running", parent_id="2"),
        ]

    def pending_inputs(self, job: str, number: int) -> list[PendingInput]:
        return [PendingInput(id="Approve", message="Ship to prod?")]

    def log(
        self, job: str, number: int, start: int = 0, node: str | None = None
    ) -> LogChunk:
        self.calls.append(("log", job, number, start, node))

        if node:
            return LogChunk(text=f"stage {node}\n", next_start=10, more=False)

        if start >= self.log_size:
            return LogChunk(text="", next_start=start, more=number == 8)

        return LogChunk(
            text=LOG.encode()[start:].decode(),
            next_start=self.log_size,
            more=number == 8,
        )

    def tests(self, job: str, number: int) -> TestReport | None:
        if number == 8:
            return None

        return TestReport(
            total=10,
            failed=1,
            skipped=2,
            failures=[TestFailure("test_x", "Suite", "boom", "trace")],
        )

    def artifacts(self, job: str, number: int) -> list[Artifact]:
        return [Artifact("dist/app.tar.gz", 4)]

    def artifact(self, job: str, number: int, path: str) -> Iterator[bytes]:
        self.calls.append(("artifact", path))
        yield b"ab"
        yield b"cd"

    def queue(self) -> list[QueueItem]:
        return [
            QueueItem(job=f"{CI_JOB}", why="Waiting for next available executor"),
            QueueItem(job="other-team/secret", why="Waiting on other-team/secret #2"),
        ]

    def executors(self) -> list[Executor]:
        return [
            Executor(node="built-in", busy=True, job=CD_JOB, number=3),
            Executor(node="agent-1", busy=True, job="other-team/secret", number=9),
            Executor(node="agent-2", busy=False),
        ]


class Silent(CIRunner):
    name = "jenkins"

    def runs(self, job: str, limit: int = 50) -> list[Run]:
        return [Run(number=1, status="success")]

    def run(self, job: str, number: int) -> Run:
        return Run(number=number, status="success")


class HelpersTest(unittest.TestCase):
    def test_capped_keeps_the_end(self):
        text = "".join(f"line {i}\n" for i in range(100_000))
        out, truncated = capped(text)

        self.assertTrue(truncated)
        self.assertLessEqual(len(out.encode()), MAX_LOG_BYTES + 100)
        self.assertTrue(out.endswith("line 99999\n"))
        self.assertTrue(out.startswith("["))
        self.assertEqual(capped("short\n"), ("short\n", False))

    def test_redact_masks_known_secret_shapes(self):
        text = redact(
            "a ghp_abcdefghijklmnopqrstuvwxyz0123456789 b AKIAABCDEFGHIJKLMNOP "
            "Authorization: Bearer abcdefghijkl c"
        )

        self.assertNotIn("ghp_", text)
        self.assertNotIn("AKIA", text)
        self.assertNotIn("abcdefghijkl c", text)
        self.assertIn("Authorization: Bearer ****", text)


@unittest.skipUnless(TestClient, "fastapi is not installed")
class PipelinesTest(GateCase):
    def setUp(self):
        super().setUp()
        from app.core.db.models import App, CiHost
        from app.repositories.configuration.config_store import ConfigStore

        registry_id = self.register()
        with self.app.state.db.session() as s:
            s.add(
                CiHost(
                    id="ci1",
                    organization_id=self.org["id"],
                    kind="jenkins",
                    name="Jenkins",
                    base_url="https://ci.acme.io",
                    token_encrypted=self.app.state.sealer.seal("tok"),
                )
            )
            s.flush()
            app = s.get(App, "a1")
            app.ci_host_id = "ci1"
            app.ci_job = CI_JOB
        store = ConfigStore(self.app.state.db)
        data = store.get(registry_id) or {}
        data["deploy"] = {
            "targets": [
                {
                    "name": "dev",
                    "kind": "aws-lambda",
                    "run_by": "jenkins",
                    "job": CD_JOB,
                    "stages": ["dev"],
                },
                {
                    "name": "gha",
                    "kind": "x",
                    "run_by": "github_actions",
                    "workflow": "d.yml",
                },
            ]
        }
        store.set(registry_id, data)
        self.runner = FakeRunner()
        self.patches = [
            mock.patch(
                "app.services.ci.service.CiService.runner_for",
                return_value=self.runner,
            ),
            mock.patch(
                "app.services.ci.service.CiService.host_runner",
                return_value=self.runner,
            ),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.base = "/api/v1/projects/p1/apps/a1/ci/runs"

    def as_viewer(self) -> None:
        from app.core.db.models import Member

        with self.app.state.db.session() as s:
            s.query(Member).update({"role": "viewer"})

    def test_runs_list_every_job_newest_first(self):
        self.as_viewer()
        res = self.client.get(self.base, headers=self.h())

        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(body["kind"], "jenkins")
        self.assertEqual(
            [(j["name"], j["kind"]) for j in body["jobs"]],
            [(CI_JOB, "ci"), (CD_JOB, "cd")],
        )
        self.assertEqual(body["jobs"][1]["label"], "dev · dev")
        self.assertEqual(
            [(r["job"], r["number"]) for r in body["runs"]],
            [(CI_JOB, 8), (CD_JOB, 3), (CI_JOB, 7)],
        )

        failed = self.client.get(
            self.base, params={"job": CI_JOB, "status": "failure"}, headers=self.h()
        ).json()
        self.assertEqual([r["number"] for r in failed["runs"]], [7])

    def test_a_job_the_app_does_not_name_is_refused(self):
        for path in ("", "/7", "/7/log", "/7/tests", "/7/artifacts"):
            res = self.client.get(
                f"{self.base}{path}",
                params={"job": "other-team/secret"},
                headers=self.h(),
            )
            self.assertEqual(res.status_code, 404, (path, res.text))

        self.assertNotIn(("runs", "other-team/secret"), self.runner.calls)

    def test_run_detail_has_stages_inputs_causes_and_masks_parameters(self):
        self.as_viewer()
        res = self.client.get(
            f"{self.base}/8", params={"job": CI_JOB}, headers=self.h()
        )

        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(body["run"]["status"], "running")
        self.assertEqual(body["causes"], ["Started by GitHub push (ana)"])
        self.assertEqual(body["parameters"]["STAGE"], "dev")
        self.assertNotIn("glpat", body["parameters"]["TOKEN"])
        self.assertEqual(body["changes"][0]["sha"], "abc1234")
        self.assertEqual(
            [(s["name"], s["parent_id"]) for s in body["stages"]],
            [("Build", None), ("Test", None), ("unit", "2"), ("e2e", "2")],
        )
        self.assertEqual(
            body["pending_inputs"], [{"id": "Approve", "message": "Ship to prod?"}]
        )
        self.assertEqual(
            body["supports"], {"log": True, "tests": True, "artifacts": True}
        )

    def test_a_runner_without_the_reads_hides_them(self):
        silent = Silent()
        with (
            mock.patch(
                "app.services.ci.service.CiService.runner_for", return_value=silent
            ),
        ):
            body = self.client.get(
                f"{self.base}/1", params={"job": CI_JOB}, headers=self.h()
            ).json()
            log = self.client.get(
                f"{self.base}/1/log", params={"job": CI_JOB}, headers=self.h()
            )

        self.assertIsNone(body["stages"])
        self.assertEqual(
            body["supports"], {"log": False, "tests": False, "artifacts": False}
        )
        self.assertEqual(log.status_code, 404)

    def test_log_follows_by_offset_and_masks_secrets(self):
        self.as_viewer()
        first = self.client.get(
            f"{self.base}/8/log", params={"job": CI_JOB}, headers=self.h()
        ).json()

        self.assertTrue(first["more"])
        self.assertIn("\x1b[32mok", first["text"])
        self.assertNotIn("ghp_", first["text"])
        nxt = self.client.get(
            f"{self.base}/8/log",
            params={"job": CI_JOB, "start": first["next_start"]},
            headers=self.h(),
        ).json()
        self.assertEqual(nxt["text"], "")
        self.assertEqual(nxt["next_start"], first["next_start"])

        stage = self.client.get(
            f"{self.base}/8/log", params={"job": CI_JOB, "node": "3"}, headers=self.h()
        ).json()
        self.assertEqual(stage["text"], "stage 3\n")
        self.assertIn(("log", CI_JOB, 8, 0, "3"), self.runner.calls)

        bad = self.client.get(
            f"{self.base}/8/log", params={"job": CI_JOB, "start": -1}, headers=self.h()
        )
        self.assertEqual(bad.status_code, 400)

    def test_log_download_streams_the_whole_console(self):
        res = self.client.get(
            f"{self.base}/7/log/download", params={"job": CI_JOB}, headers=self.h()
        )

        self.assertEqual(res.status_code, 200)
        self.assertIn("attachment", res.headers["content-disposition"])
        self.assertIn("ok", res.text)
        self.assertNotIn("ghp_", res.text)

    def test_tests_and_artifacts(self):
        self.as_viewer()
        report = self.client.get(
            f"{self.base}/7/tests", params={"job": CI_JOB}, headers=self.h()
        ).json()["report"]

        self.assertEqual(
            (report["total"], report["passed"], report["failed"]), (10, 7, 1)
        )
        self.assertEqual(report["failures"][0]["name"], "test_x")
        self.assertIsNone(
            self.client.get(
                f"{self.base}/8/tests", params={"job": CI_JOB}, headers=self.h()
            ).json()["report"]
        )

        listed = self.client.get(
            f"{self.base}/7/artifacts", params={"job": CI_JOB}, headers=self.h()
        ).json()
        self.assertEqual(listed["artifacts"], [{"path": "dist/app.tar.gz", "size": 4}])

        res = self.client.get(
            f"{self.base}/7/artifacts/download",
            params={"job": CI_JOB, "path": "dist/app.tar.gz"},
            headers=self.h(),
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content, b"abcd")
        self.assertEqual(res.headers["content-type"], "application/octet-stream")
        self.assertIn('filename="app.tar.gz"', res.headers["content-disposition"])

        unlisted = self.client.get(
            f"{self.base}/7/artifacts/download",
            params={"job": CI_JOB, "path": "../../credentials.xml"},
            headers=self.h(),
        )
        self.assertEqual(unlisted.status_code, 404)
        self.assertNotIn(("artifact", "../../credentials.xml"), self.runner.calls)

    def test_upstream_failure_is_a_502(self):
        with mock.patch.object(FakeRunner, "run", side_effect=ProviderError("refused")):
            res = self.client.get(
                f"{self.base}/7", params={"job": CI_JOB}, headers=self.h()
            )

        self.assertEqual(res.status_code, 502)

    def test_a_token_limited_to_another_app_cannot_read(self):
        from app.core.db.models import App

        with self.app.state.db.session() as s:
            s.add(App(id="a2", project_id="p1", registry_id="r2", name="other"))
        token = self.token(f"read org:{self.org['id']} project:p1 app:a2")
        mine = self.token(f"read org:{self.org['id']} project:p1 app:a1")

        self.assertEqual(
            self.client.get(self.base, headers=self.h(mine)).status_code, 200
        )
        self.assertEqual(
            self.client.get(self.base, headers=self.h(token)).status_code, 404
        )
        self.assertEqual(
            self.client.get(
                f"{self.base}/7/log", params={"job": CI_JOB}, headers=self.h(token)
            ).status_code,
            404,
        )

    def test_outsiders_cannot_read(self):
        self.assertEqual(self.client.get(self.base).status_code, 401)

    def test_activity_names_only_the_callers_jobs(self):
        self.as_viewer()
        res = self.client.get("/api/v1/ci-hosts/activity", headers=self.h())

        self.assertEqual(res.status_code, 200, res.text)
        host = res.json()["hosts"][0]
        self.assertEqual(host["name"], "Jenkins")
        self.assertEqual(host["queue"][0]["app"]["app_id"], "a1")
        self.assertEqual(host["queue"][0]["why"], "Waiting for next available executor")
        self.assertEqual(host["queue"][1], {"since": None, "why": None, "app": None})
        self.assertEqual(
            [
                (e["node"], e["busy"], e["number"], (e["app"] or {}).get("job"))
                for e in host["executors"]
            ],
            [
                ("built-in", True, 3, CD_JOB),
                ("agent-1", True, None, None),
                ("agent-2", False, None, None),
            ],
        )
        self.assertNotIn("other-team", res.text)
