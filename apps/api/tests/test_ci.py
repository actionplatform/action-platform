"""App › CI: CI servers of the organization, the app's link to one, and the runs imported from it."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest import mock

from action_platform.core.context import Run
from action_platform.core.exception import ProviderError
from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


RUNS = [
    Run(
        number=7,
        status="success",
        url="https://ci.acme.io/job/app/7/",
        branch="main",
        sha="abc",
        trigger="push",
        started_at=datetime(2026, 9, 17, 10, 0, tzinfo=timezone.utc),
        duration_ms=12_000,
        name="#7",
    ),
    Run(number=6, status="failure", branch="main"),
]


@unittest.skipUnless(TestClient, "fastapi is not installed")
class CiTest(GateCase):
    def add_jenkins(self) -> str:
        res = self.client.post(
            "/api/v1/ci-hosts",
            json={
                "kind": "jenkins",
                "base_url": "https://ci.acme.io/",
                "token": "tok",
                "username": "ada",
            },
            headers=self.h(),
        )
        self.assertEqual(res.status_code, 201, res.text)

        return res.json()["id"]

    def test_ci_hosts_are_listed_and_removed(self):
        host_id = self.add_jenkins()
        listed = self.client.get("/api/v1/ci-hosts", headers=self.h()).json()

        self.assertEqual(
            [(h["kind"], h["name"], h["base_url"]) for h in listed],
            [("jenkins", "Jenkins", "https://ci.acme.io")],
        )
        self.assertNotIn("token", listed[0])

        res = self.client.delete(f"/api/v1/ci-hosts/{host_id}", headers=self.h())
        self.assertEqual(res.status_code, 204)
        self.assertEqual(
            self.client.get("/api/v1/ci-hosts", headers=self.h()).json(), []
        )

    def test_unknown_kind_and_missing_token_are_refused(self):
        for body in (
            {"kind": "teamcity", "base_url": "https://x", "token": "t"},
            {"kind": "jenkins", "base_url": "https://x", "token": " "},
            {"kind": "jenkins", "base_url": "", "token": "t"},
        ):
            res = self.client.post("/api/v1/ci-hosts", json=body, headers=self.h())
            self.assertEqual(res.status_code, 400, res.text)

    def test_test_reaches_the_server_with_the_sealed_token(self):
        host_id = self.add_jenkins()

        with mock.patch("action_platform.providers.ci.jenkins.rest.call") as call:
            call.return_value = {"mode": "NORMAL"}
            res = self.client.post(f"/api/v1/ci-hosts/{host_id}/test", headers=self.h())

        self.assertEqual(res.json(), {"ok": True, "error": None})
        url, headers = call.call_args.args[1], call.call_args.args[2]
        self.assertEqual(url, "https://ci.acme.io/api/json?tree=mode")
        self.assertTrue(headers["authorization"].startswith("Basic "))

        with mock.patch("action_platform.providers.ci.jenkins.rest.call") as call:
            call.side_effect = ProviderError("GET … → 401: bad token")
            res = self.client.post(f"/api/v1/ci-hosts/{host_id}/test", headers=self.h())

        self.assertFalse(res.json()["ok"])
        self.assertIn("401", res.json()["error"])

    def test_link_sync_and_read(self):
        self.register()
        host_id = self.add_jenkins()
        base = "/api/v1/projects/p1/apps/a1/ci"

        before = self.client.get(base, headers=self.h()).json()
        self.assertEqual(
            before["link"], {"kind": "none", "ci_host_id": None, "job": ""}
        )
        self.assertEqual(before["runs"], [])

        res = self.client.put(
            base, json={"ci_host_id": host_id, "job": "team/app/main"}, headers=self.h()
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(
            res.json(),
            {"kind": "jenkins", "ci_host_id": host_id, "job": "team/app/main"},
        )

        with mock.patch(
            "action_platform.providers.ci.jenkins.CIJenkins.runs", return_value=RUNS
        ) as runs:
            res = self.client.post(f"{base}/sync", headers=self.h())

        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(runs.call_args.args[0], "team/app/main")
        body = res.json()
        self.assertIsNone(body["error"])
        self.assertEqual([r["number"] for r in body["runs"]], [7, 6])
        self.assertEqual(body["runs"][0]["status"], "success")
        self.assertEqual(body["runs"][0]["source"], "jenkins")
        self.assertEqual(body["runs"][0]["duration_ms"], 12_000)

        with mock.patch(
            "action_platform.providers.ci.jenkins.CIJenkins.runs",
            return_value=[Run(number=7, status="failure", branch="main")],
        ):
            self.client.post(f"{base}/sync", headers=self.h())

        after = self.client.get(base, headers=self.h()).json()
        self.assertEqual(
            [(r["number"], r["status"]) for r in after["runs"]],
            [(7, "failure"), (6, "failure")],
        )

    def test_sync_reports_the_provider_error(self):
        self.register()
        host_id = self.add_jenkins()
        base = "/api/v1/projects/p1/apps/a1/ci"
        self.client.put(
            base, json={"ci_host_id": host_id, "job": "app"}, headers=self.h()
        )

        with mock.patch(
            "action_platform.providers.ci.jenkins.rest.call",
            side_effect=ProviderError("cannot reach https://ci.acme.io: refused"),
        ):
            res = self.client.post(f"{base}/sync", headers=self.h())

        self.assertEqual(res.status_code, 200)
        self.assertIn("cannot reach", res.json()["error"])

    def test_unknown_ci_host_cannot_be_linked(self):
        self.register()
        res = self.client.put(
            "/api/v1/projects/p1/apps/a1/ci",
            json={"ci_host_id": "nope", "job": "x"},
            headers=self.h(),
        )
        self.assertEqual(res.status_code, 404)

    def test_github_source_host_means_github_actions(self):
        from app.core.db.models import App, SourceHost

        self.register()
        with self.app.state.db.session() as s:
            s.add(
                SourceHost(
                    id="h1",
                    organization_id=self.org["id"],
                    kind="github",
                    name="GitHub",
                    auth_kind="token",
                    token_encrypted=self.app.state.sealer.seal("ghp_secret"),
                )
            )
            s.get(App, "a1").source_host_id = "h1"

        link = self.client.get(
            "/api/v1/projects/p1/apps/a1/ci", headers=self.h()
        ).json()["link"]
        self.assertEqual(link["kind"], "github_actions")

        with mock.patch(
            "action_platform.providers.ci.github_actions.CIGithubActions.runs",
            return_value=[Run(number=1, status="success")],
        ) as runs:
            res = self.client.post(
                "/api/v1/projects/p1/apps/a1/ci/sync", headers=self.h()
            )

        self.assertEqual(res.json()["runs"][0]["source"], "github_actions")
        self.assertEqual(runs.call_args.args[0], "")
