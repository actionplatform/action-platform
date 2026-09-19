from __future__ import annotations

import unittest
from unittest import mock

from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient, "fastapi is not installed")
class ScopesTest(GateCase):
    def setUp(self):
        super().setUp()
        from app.repositories.configuration.config_store import ConfigStore

        self.registry_id = self.register()
        ConfigStore(self.app.state.db).set(
            self.registry_id,
            {
                "project": {"name": "demo"},
                "deploy": {"target": "aws/lambda", "region": "us-east-1"},
            },
        )
        self.base = "/api/v1/projects/p1/apps/a1/scopes"

    def test_the_configuration_derives_dev_and_prod_on_first_sight(self):
        body = self.client.get(self.base, headers=self.h()).json()

        self.assertEqual(
            [
                (s["name"], s["kind"], s["criticality"], s["target"], s["derived"])
                for s in body["items"]
            ],
            [
                ("dev", "web", "test", "aws/lambda", True),
                ("prod", "web", "high", "aws/lambda", True),
            ],
        )
        self.assertEqual(body["items"][0]["options"], {"region": "us-east-1"})
        self.assertEqual(
            body["criticalities"], ["test", "low", "medium", "high", "critical"]
        )

    def test_create_update_delete(self):
        created = self.client.post(
            self.base,
            json={
                "name": "staging",
                "kind": "web",
                "criticality": "low",
                "target": "aws/lambda",
                "options": {"region": "eu-west-1"},
            },
            headers=self.h(),
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(
            [s["name"] for s in created.json()["items"]], ["dev", "prod", "staging"]
        )

        twice = self.client.post(self.base, json={"name": "staging"}, headers=self.h())
        self.assertEqual(twice.status_code, 409)

        bad = self.client.post(
            self.base, json={"name": "qa", "criticality": "urgent"}, headers=self.h()
        )
        self.assertEqual(bad.status_code, 400)
        self.assertIn("criticality", bad.json()["detail"])

        updated = self.client.put(
            f"{self.base}/staging",
            json={"kind": "job", "criticality": "medium"},
            headers=self.h(),
        )
        row = next(s for s in updated.json()["items"] if s["name"] == "staging")
        self.assertEqual(
            (row["kind"], row["criticality"], row["derived"]), ("job", "medium", False)
        )

        gone = self.client.delete(f"{self.base}/staging", headers=self.h())
        self.assertEqual([s["name"] for s in gone.json()["items"]], ["dev", "prod"])

        missing = self.client.delete(f"{self.base}/staging", headers=self.h())
        self.assertEqual(missing.status_code, 404)

    def test_a_deploy_needs_an_existing_scope_and_scope_is_an_alias_of_stage(self):
        headers = {**self.h(), "Prefer": "respond-async"}

        unknown = self.client.post(
            f"/api/v1/apps/{self.registry_id}/deploy",
            json={"scope": "qa", "version": "1.2.3", "dry_run": False},
            headers=headers,
        )
        self.assertEqual(unknown.status_code, 400, unknown.text)
        self.assertIn("no scope 'qa'", unknown.json()["detail"])

        ok = self.client.post(
            f"/api/v1/apps/{self.registry_id}/deploy",
            json={"scope": "prod", "version": "1.2.3", "dry_run": False},
            headers=headers,
        )
        self.assertEqual(ok.status_code, 202, ok.text)

        from app.core.db.models import Job
        import json

        with self.app.state.db.session() as s:
            payload = json.loads(s.get(Job, ok.json()["job"]).payload)

        self.assertEqual(payload["body"]["stage"], "prod")
        self.assertNotIn("scope", payload["body"])

    def test_a_release_cut_here_gets_its_shape_and_readiness_per_scope(self):
        from sqlalchemy import select

        from app.core.db.models import Job, Release
        from app.repositories.workspace.source import get_registry
        from app.services.jobs.handlers import JobHandlers
        from app.services.releases import ReleasesService

        self.client.post(
            self.base, json={"name": "staging", "criticality": "low"}, headers=self.h()
        )
        handlers = JobHandlers(self.app.state.db, self.app.state.sealer, get_registry())
        payload = {
            "path": f"apps/{self.registry_id}/release",
            "method": "POST",
            "body": {"level": "patch", "dry_run": False, "branch": "hotfix/9-login"},
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
                return_value={"current": "1.2.3", "next": "1.2.4", "changelog": ""},
            ),
            mock.patch.object(JobHandlers, "import_activity", return_value={}),
            mock.patch.object(JobHandlers, "_snapshot"),
        ):
            handlers.release(payload)

        with self.app.state.db.session() as s:
            release = s.scalar(select(Release).where(Release.tag == "v1.2.4"))
            keys = sorted(
                j.dedupe_key
                for j in s.scalars(select(Job).where(Job.kind == "readiness"))
            )

        self.assertEqual(release.shape, "hotfix")
        self.assertEqual(
            keys,
            [
                "readiness:v1.2.4:dev",
                "readiness:v1.2.4:prod",
                "readiness:v1.2.4:staging",
            ],
        )

    def test_readiness_carries_the_scope_shape_check(self):
        from app.core.db.models import Release
        from app.repositories.releases import ReleaseStore
        from app.repositories.workspace.source import get_registry
        from app.services.jobs.handlers import JobHandlers

        from action_platform.testing.fixtures import git

        git(self.repo, "tag", "v1.3.0-rc.1")
        self.client.post(
            f"/api/v1/apps/{self.registry_id}/sync", json={}, headers=self.h()
        )

        with self.app.state.db.session() as s:
            ReleaseStore(s).ensure("a1", "v1.3.0-rc.1", "git")

        handlers = JobHandlers(self.app.state.db, self.app.state.sealer, get_registry())
        payload = {
            "path": f"apps/{self.registry_id}/readiness",
            "method": "POST",
            "body": {"tag": "v1.3.0-rc.1", "stage": "prod"},
            "registry_id": self.registry_id,
            "organization_id": self.org["id"],
            "app_id": "a1",
            "job_id": "j2",
            "user_id": self.user_id,
        }

        result = handlers.readiness(payload)
        checks = {c["id"]: c for c in result["checks"]}

        self.assertFalse(result["ok"])
        self.assertFalse(checks["scope.release-shape"]["ok"])
        self.assertIn("candidate", checks["scope.release-shape"]["detail"])
        self.assertEqual(checks["deploy.stage"]["detail"], "prod · web · high")

        with self.app.state.db.session() as s:
            self.assertEqual(
                s.scalar(
                    __import__("sqlalchemy")
                    .select(Release)
                    .where(Release.tag == "v1.3.0-rc.1")
                ).shape,
                "candidate",
            )
