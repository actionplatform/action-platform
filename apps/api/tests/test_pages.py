"""Server-side pages: releases, pull requests, CI runs and jobs answer with items, total, page and per."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from action_platform.core.context import Run
from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient, "fastapi is not installed")
class PagesTest(GateCase):
    def setUp(self):
        super().setUp()
        self.registry_id = self.register()

    def test_releases_page(self):
        from app.repositories.releases import ReleaseStore

        with self.app.state.db.session() as s:
            for i in range(23):
                ReleaseStore(s).ensure(
                    "a1",
                    f"v1.0.{i}",
                    "git",
                    published_at=datetime(2026, 1, 1 + i % 28, tzinfo=timezone.utc),
                )

        base = "/api/v1/projects/p1/apps/a1/releases"
        first = self.client.get(f"{base}?page=1&per=10", headers=self.h()).json()
        self.assertEqual(
            (first["total"], first["page"], first["per"], len(first["items"])),
            (23, 1, 10, 10),
        )
        last = self.client.get(f"{base}?page=3&per=10", headers=self.h()).json()
        self.assertEqual(len(last["items"]), 3)
        self.assertNotEqual(first["items"][0]["tag"], last["items"][0]["tag"])
        clamped = self.client.get(f"{base}?page=0&per=1000", headers=self.h()).json()
        self.assertEqual((clamped["page"], clamped["per"]), (1, 100))

    def test_pull_requests_page(self):
        from app.core.db.models import PullRequest

        with self.app.state.db.session() as s:
            for i in range(12):
                s.add(
                    PullRequest(
                        id=f"pr{i}",
                        app_id="a1",
                        number=i + 1,
                        title=f"PR {i}",
                        url="https://x",
                        head=f"feature/{i}",
                        base="develop",
                        state="open",
                        draft=False,
                        created_at=datetime(2026, 1, 1, i),
                        updated_at=datetime(2026, 1, 1, i),
                        source="github",
                    )
                )

        body = self.client.get(
            "/api/v1/projects/p1/apps/a1/pull-requests?page=2&per=10", headers=self.h()
        ).json()
        self.assertEqual((body["total"], body["page"], len(body["items"])), (12, 2, 2))
        self.assertEqual(body["items"][0]["number"], 2)

    def test_ci_runs_page(self):
        from unittest import mock

        from app.core.db.models import App, SourceHost

        with self.app.state.db.session() as s:
            s.add(
                SourceHost(
                    id="h1",
                    organization_id=self.org["id"],
                    kind="github",
                    name="GitHub",
                    auth_kind="token",
                    token_encrypted=self.app.state.sealer.seal("ghp"),
                )
            )
            s.get(App, "a1").source_host_id = "h1"

        runs = [Run(number=n, status="success", branch="main") for n in range(1, 16)]
        with mock.patch(
            "action_platform.providers.ci.github_actions.CIGithubActions.runs",
            return_value=runs,
        ):
            body = self.client.post(
                "/api/v1/projects/p1/apps/a1/ci/sync?per=5", headers=self.h()
            ).json()

        self.assertEqual(
            (body["total"], body["page"], body["per"], len(body["runs"])), (15, 1, 5, 5)
        )
        self.assertEqual(body["runs"][0]["number"], 15)
        page3 = self.client.get(
            "/api/v1/projects/p1/apps/a1/ci?page=3&per=5", headers=self.h()
        ).json()
        self.assertEqual([r["number"] for r in page3["runs"]], [5, 4, 3, 2, 1])

    def test_jobs_page(self):
        from app.services.jobs import JobQueue

        queue = JobQueue(self.app.state.db)
        for i in range(7):
            queue.enqueue(
                "deploy" if i % 2 else "destroy",
                {"body": {"stage": "dev"}},
                organization_id=self.org["id"],
                app_id="a1",
            )
        queue.enqueue("sync", {}, organization_id=self.org["id"], app_id="a1")

        body = self.client.get(
            f"/api/v1/jobs?app={self.registry_id}&per=5", headers=self.h()
        ).json()
        self.assertEqual((body["total"], body["page"], len(body["items"])), (8, 1, 5))
        legacy = self.client.get(
            f"/api/v1/jobs/page?app={self.registry_id}&per=5", headers=self.h()
        ).json()
        self.assertEqual((legacy["total"], len(legacy["items"])), (7, 5))
        only = self.client.get(
            f"/api/v1/jobs?app={self.registry_id}&kinds=deploy&per=10",
            headers=self.h(),
        ).json()
        self.assertEqual(only["total"], 3)


@unittest.skipUnless(TestClient, "fastapi is not installed")
class ListPagesTest(GateCase):
    def get(self, path: str):
        res = self.client.get(path, headers=self.h())
        self.assertEqual(res.status_code, 200, res.text)

        return res.json()

    def assertPaged(self, path: str, total: int, per: int = 2):
        plain = self.get(path)
        self.assertIsInstance(plain, list)
        self.assertEqual(len(plain), total)

        sep = "&" if "?" in path else "?"
        pages = -(-total // per)
        first = self.get(f"{path}{sep}page=1&per={per}")
        self.assertEqual(
            (first["total"], first["page"], first["per"], len(first["items"])),
            (total, 1, per, min(per, total)),
        )
        last = self.get(f"{path}{sep}page={pages}&per={per}")
        self.assertEqual(len(last["items"]), total - per * (pages - 1))
        self.assertEqual(
            self.get(f"{path}{sep}page={pages + 1}&per={per}")["items"], []
        )

    def test_teams_members_and_invitations(self):
        for name in ("A", "B", "C"):
            self.client.post("/api/v1/teams", json={"name": name}, headers=self.h())

        self.assertPaged("/api/v1/teams", 3)
        self.assertPaged("/api/v1/members", 1, per=1)
        for email in ("x@example.com", "y@example.com", "z@example.com"):
            res = self.client.post(
                "/api/v1/invitations",
                json={"email": email, "role": "viewer"},
                headers=self.h(),
            )
            self.assertEqual(res.status_code, 201, res.text)

        self.assertPaged("/api/v1/invitations", 3)

    def test_projects_hosts_and_ci_hosts(self):
        for name in ("A", "B", "C"):
            self.client.post("/api/v1/projects", json={"name": name}, headers=self.h())
        for i in range(3):
            self.client.post(
                "/api/v1/hosts",
                json={"kind": "github", "name": f"gh{i}", "token": "t"},
                headers=self.h(),
            )
            self.client.post(
                "/api/v1/ci-hosts",
                json={
                    "kind": "jenkins",
                    "name": f"ci{i}",
                    "base_url": "https://ci.example.com",
                    "token": "t",
                    "username": "u",
                },
                headers=self.h(),
            )

        self.assertPaged("/api/v1/projects", 3)
        self.assertPaged("/api/v1/hosts", 3)
        self.assertPaged("/api/v1/ci-hosts", 3)

    def test_tokens_and_sessions(self):
        for _ in range(2):
            self.client.post(
                "/api/auth/tokens",
                json={"scope": "read", "name": "t"},
                headers=self.h(),
            )

        self.assertPaged("/api/auth/tokens", 2, per=1)
        listed = self.get("/api/auth/sessions")
        self.assertPaged("/api/auth/sessions", len(listed), per=1)

    def test_ci_activity_keeps_its_shape_and_adds_the_page(self):
        activity = self.get("/api/v1/ci-hosts/activity")
        self.assertNotIn("total", activity)
        paged = self.get("/api/v1/ci-hosts/activity?page=1")
        self.assertEqual((paged["total"], paged["page"], paged["hosts"]), (0, 1, []))
