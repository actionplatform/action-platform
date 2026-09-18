from __future__ import annotations

import unittest
from unittest import mock

from action_platform.core.context import Check
from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient, "fastapi is not installed")
class ReadinessTest(GateCase):
    def setUp(self):
        super().setUp()
        self.registry_id = self.register()
        self.base = "/api/v1/projects/p1/apps/a1"

        with self.app.state.db.session() as s:
            from app.repositories.releases import ReleaseStore

            self.release_id = ReleaseStore(s).ensure("a1", "v1.2.3", "git").id

    def stored(self, stage: str, checks: list[Check]) -> None:
        from app.core.db.models import Release
        from app.repositories.releases import ReadinessStore

        with self.app.state.db.session() as s:
            ReadinessStore(s).done(s.get(Release, self.release_id), stage, checks, "j1")

    def test_the_release_page_carries_a_verdict_per_stage(self):
        self.stored("dev", [Check("aws.credentials", True, "ok")])
        self.stored(
            "prod",
            [
                Check("aws.permissions", False, "may not lambda:GetLayerVersion"),
                Check("lockfile.pyproject.toml", False, "none", severity="warning"),
            ],
        )

        with self.app.state.db.session() as s:
            from app.core.db.models import Release
            from app.repositories.releases import ReadinessStore

            ReadinessStore(s).queued(s.get(Release, self.release_id), "prod", "j2")

        page = self.client.get(f"{self.base}/releases", headers=self.h()).json()

        self.assertEqual(
            page["items"][0]["readiness"], {"dev": "ok", "prod": "pending"}
        )

    def test_a_warning_alone_keeps_the_release_deployable(self):
        self.stored(
            "prod",
            [Check("lockfile.pyproject.toml", False, "none", severity="warning")],
        )

        rows = self.client.get(
            f"{self.base}/releases/v1.2.3/readiness", headers=self.h()
        ).json()

        self.assertEqual((rows[0]["stage"], rows[0]["verdict"]), ("prod", "ok"))
        self.assertEqual(rows[0]["checks"][0]["severity"], "warning")

    def test_a_blocked_release_refuses_the_deploy_unless_forced(self):
        self.stored(
            "prod", [Check("aws.permissions", False, "may not lambda:GetLayerVersion")]
        )
        headers = {**self.h(), "Prefer": "respond-async"}

        refused = self.client.post(
            f"/api/v1/apps/{self.registry_id}/deploy",
            json={"stage": "prod", "version": "1.2.3", "dry_run": False},
            headers=headers,
        )
        dev = self.client.post(
            f"/api/v1/apps/{self.registry_id}/deploy",
            json={"stage": "dev", "version": "1.2.3", "dry_run": False},
            headers=headers,
        )
        forced = self.client.post(
            f"/api/v1/apps/{self.registry_id}/deploy",
            json={"stage": "prod", "version": "1.2.3", "dry_run": False, "force": True},
            headers=headers,
        )

        self.assertEqual(refused.status_code, 409, refused.text)
        self.assertIn("not deployable to prod", refused.json()["detail"])
        self.assertIn("lambda:GetLayerVersion", refused.json()["detail"])
        self.assertEqual(dev.status_code, 202, dev.text)
        self.assertEqual(forced.status_code, 202, forced.text)

    def test_asking_for_a_check_queues_one_job_per_stage(self):
        from app.core.db.models import Job
        from sqlalchemy import select

        res = self.client.post(
            f"{self.base}/releases/v1.2.3/readiness", json={}, headers=self.h()
        )

        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(len(res.json()["jobs"]), 2)
        self.assertEqual(
            [(r["stage"], r["verdict"]) for r in res.json()["readiness"]],
            [("dev", "pending"), ("prod", "pending")],
        )

        with self.app.state.db.session() as s:
            jobs = list(s.scalars(select(Job).where(Job.kind == "readiness")))

        self.assertEqual(
            sorted(j.dedupe_key for j in jobs),
            ["readiness:v1.2.3:dev", "readiness:v1.2.3:prod"],
        )

        again = self.client.post(
            f"{self.base}/releases/v1.2.3/readiness",
            json={"stage": "prod"},
            headers=self.h(),
        )

        self.assertEqual(
            again.json()["jobs"][0],
            next(j.id for j in jobs if j.dedupe_key.endswith("prod")),
        )

    def test_the_worker_stores_the_checks_it_ran(self):
        from app.repositories.workspace.source import get_registry
        from app.services.jobs.handlers import JobHandlers
        from app.services.releases.readiness import ReadinessService

        handlers = JobHandlers(self.app.state.db, self.app.state.sealer, get_registry())
        payload = {
            "path": f"apps/{self.registry_id}/readiness",
            "method": "POST",
            "body": {"tag": "v1.2.3", "stage": "prod"},
            "registry_id": self.registry_id,
            "organization_id": self.org["id"],
            "app_id": "a1",
            "job_id": "j9",
            "user_id": self.user_id,
        }

        with mock.patch.object(
            ReadinessService,
            "check",
            return_value=[Check("deploy.targets", False, "none", level="static")],
        ):
            result = handlers.readiness(payload)

        self.assertFalse(result["ok"])

        rows = self.client.get(
            f"{self.base}/releases/v1.2.3/readiness", headers=self.h()
        ).json()

        self.assertEqual(
            (rows[0]["stage"], rows[0]["verdict"], rows[0]["job_id"]),
            ("prod", "blocked", "j9"),
        )
        self.assertEqual(rows[0]["checks"][0]["id"], "deploy.targets")

    def test_a_release_cut_here_queues_its_readiness(self):
        from app.core.db.models import Job
        from app.repositories.workspace.source import get_registry
        from app.services.jobs.handlers import JobHandlers
        from app.services.releases import ReleasesService
        from sqlalchemy import select

        handlers = JobHandlers(self.app.state.db, self.app.state.sealer, get_registry())
        payload = {
            "path": f"apps/{self.registry_id}/release",
            "method": "POST",
            "body": {"level": "minor", "dry_run": False},
            "registry_id": self.registry_id,
            "organization_id": self.org["id"],
            "app_id": "a1",
            "job_id": "j1",
            "user_id": self.user_id,
            "manages": True,
        }

        with (
            mock.patch.object(
                ReleasesService,
                "release",
                return_value={"current": "1.2.3", "next": "1.3.0", "changelog": ""},
            ),
            mock.patch.object(JobHandlers, "import_activity", return_value={}),
            mock.patch.object(JobHandlers, "_snapshot"),
        ):
            handlers.release(payload)

        with self.app.state.db.session() as s:
            keys = sorted(
                j.dedupe_key
                for j in s.scalars(select(Job).where(Job.kind == "readiness"))
            )

        self.assertEqual(keys, ["readiness:v1.3.0:dev", "readiness:v1.3.0:prod"])
