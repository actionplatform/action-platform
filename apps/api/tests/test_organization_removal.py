from __future__ import annotations

import unittest

from sqlalchemy import select

from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient, "fastapi is not installed")
class OrganizationRemovalTest(GateCase):
    def test_an_owner_deletes_everything_the_organization_owned(self):
        from app.core.db.models import App, Job, Member, Organization, Project, Session

        registry_id = self.register()
        self.client.post(
            f"/api/v1/apps/{registry_id}/sync",
            json={},
            headers={**self.h(), "Prefer": "respond-async"},
        )
        org_id = self.org["id"]

        wrong = self.client.delete(
            f"/api/v1/organizations/{org_id}",
            params={"confirm": "nope"},
            headers=self.h(),
        )
        self.assertEqual(wrong.status_code, 400, wrong.text)

        res = self.client.delete(
            f"/api/v1/organizations/{org_id}",
            params={"confirm": "acme"},
            headers=self.h(),
        )

        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["removed"], [registry_id])

        with self.app.state.db.session() as s:
            self.assertIsNone(s.get(Organization, org_id))
            self.assertEqual(s.scalars(select(Project)).all(), [])
            self.assertEqual(s.scalars(select(App)).all(), [])
            self.assertEqual(s.scalars(select(Member)).all(), [])
            self.assertEqual(
                s.scalars(select(Job).where(Job.organization_id == org_id)).all(), []
            )
            self.assertTrue(
                all(
                    x.active_organization_id != org_id
                    for x in s.scalars(select(Session))
                )
            )

        self.assertEqual(
            self.client.get(
                "/api/apps", headers={"authorization": "Bearer shared"}
            ).json(),
            [],
        )

    def test_a_non_owner_is_refused(self):
        from app.core.db.models import Member

        with self.app.state.db.session() as s:
            member = s.scalar(select(Member).where(Member.user_id == self.user_id))
            member.role = "admin"

        res = self.client.delete(
            f"/api/v1/organizations/{self.org['id']}",
            params={"confirm": "acme"},
            headers=self.h(),
        )

        self.assertEqual(res.status_code, 403, res.text)

    def test_with_cloud_the_worker_tears_down_then_removes(self):
        from unittest import mock

        from app.core.db.models import Organization
        from app.repositories.workspace.source import get_registry
        from app.services.deployments import DeploymentsService
        from app.services.jobs.handlers import JobHandlers
        from app.services.jobs import JobQueue

        self.register()
        res = self.client.delete(
            f"/api/v1/organizations/{self.org['id']}",
            params={"confirm": "acme", "cloud": "true"},
            headers=self.h(),
        )

        self.assertEqual(res.status_code, 202, res.text)
        job = JobQueue(self.app.state.db).get(res.json()["job"])
        payload = __import__("json").loads(job.payload)
        payload["job_id"] = job.id

        with mock.patch.object(DeploymentsService, "destroy") as destroy:
            result = JobHandlers(
                self.app.state.db, self.app.state.sealer, get_registry()
            ).destroy_organization(payload)

        destroy.assert_called_once()
        self.assertEqual(result["organization"], "acme")

        with self.app.state.db.session() as s:
            self.assertIsNone(s.get(Organization, self.org["id"]))
