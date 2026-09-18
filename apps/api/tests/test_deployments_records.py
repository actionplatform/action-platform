"""App › Deployments as records: what the worker shipped, what an observed pipeline shipped, and whether the version is at the destination."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from action_platform.core.context import DeployResult, Run
from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

TARGETS = {
    "targets": [
        {"name": "lambda", "kind": "aws/lambda", "stages": ["dev", "prod"]},
        {
            "name": "pypi",
            "kind": "pypi",
            "run_by": "github_actions",
            "workflow": "publish.yml",
            "package": "demo",
        },
        {
            "name": "ghcr",
            "kind": "docker",
            "run_by": "jenkins",
            "job": "team/demo/publish",
            "image": "ghcr.io/acme/demo",
            "component": "api",
        },
    ]
}


def run(
    number: int, branch: str, status: str = "success", started: datetime | None = None
) -> Run:
    return Run(
        number=number,
        status=status,
        branch=branch,
        sha=f"sha{number}",
        url=f"https://ci/{number}",
        trigger="push",
        started_at=started
        or datetime(2026, 9, 17, 10, 0, tzinfo=timezone.utc)
        + timedelta(seconds=number),
        duration_ms=60_000,
    )


@unittest.skipUnless(TestClient, "fastapi is not installed")
class DeploymentRecordsTest(GateCase):
    def setUp(self):
        super().setUp()
        from app.repositories.configuration.config_store import ConfigStore

        self.registry_id = self.register()
        ConfigStore(self.app.state.db).set(
            self.registry_id, {"project": {"name": "demo"}, "deploy": TARGETS}
        )
        self.base = "/api/v1/projects/p1/apps/a1/deployments"

    def github(self):
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

    def jenkins(self):
        from app.core.db.models import App

        host = self.client.post(
            "/api/v1/ci-hosts",
            json={
                "kind": "jenkins",
                "base_url": "https://ci.acme.io",
                "token": "t",
                "username": "u",
            },
            headers=self.h(),
        ).json()
        with self.app.state.db.session() as s:
            s.get(App, "a1").ci_host_id = host["id"]

    def test_targets_are_listed_with_their_executor(self):
        body = self.client.get(self.base, headers=self.h()).json()

        self.assertEqual(
            [(t["name"], t["kind"], t["run_by"]) for t in body["targets"]],
            [
                ("lambda", "aws/lambda", "platform"),
                ("pypi", "pypi", "github_actions"),
                ("ghcr", "docker", "jenkins"),
            ],
        )
        self.assertEqual(body["targets"][1]["workflow"], "publish.yml")
        self.assertEqual(body["deployments"], [])

    def test_the_worker_records_what_it_shipped(self):
        from app.core.db.models import App
        from app.repositories.configuration.config_store import ConfigStore
        from app.services.deployments import DeploymentRecords

        with self.app.state.db.session() as s:
            rows = DeploymentRecords(s, self.app.state.sealer).record_platform(
                s.get(App, "a1"),
                ConfigStore(self.app.state.db).config_of(self.registry_id),
                [
                    DeployResult(
                        ok=True,
                        target="lambda",
                        version="1.2.0",
                        url="https://x.lambda-url",
                    )
                ],
                "prod",
                "job-1",
                "Ana",
                datetime(2026, 9, 17, 9, 0),
            )
            self.assertEqual(rows[0].executor, "platform")

        body = self.client.get(self.base, headers=self.h()).json()
        row = body["deployments"][0]
        self.assertEqual(
            (
                row["target"],
                row["stage"],
                row["version"],
                row["status"],
                row["executor"],
                row["job_id"],
                row["actor"],
            ),
            ("lambda", "prod", "1.2.0", "success", "platform", "job-1", "Ana"),
        )

    def test_observed_runs_on_a_tag_become_deployments_and_are_verified(self):
        self.github()
        runs = [
            run(9001, "v1.4.0"),
            run(9000, "main"),
            run(8999, "v1.3.0", "failure"),
            run(8998, "feature/x", "success"),
        ]

        with (
            mock.patch(
                "action_platform.providers.ci.github_actions.CIGithubActions.runs",
                return_value=runs,
            ) as listed,
            mock.patch(
                "action_platform.providers.deploy.pypi.DeployPypi.verify",
                side_effect=lambda v, s=None: v == "1.4.0",
            ) as verify,
        ):
            res = self.client.post(f"{self.base}/sync", headers=self.h())

        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(listed.call_args.args[0], "publish.yml")
        body = res.json()
        pypi = [d for d in body["deployments"] if d["target"] == "pypi"]
        self.assertEqual(
            [(d["version"], d["status"]) for d in pypi],
            [("1.4.0", "verified"), ("1.3.0", "failure")],
        )
        self.assertEqual(pypi[0]["url"], "https://ci/9001")
        self.assertEqual(pypi[0]["executor"], "github_actions")
        self.assertIsNotNone(pypi[0]["verified_at"])
        self.assertEqual(verify.call_count, 1)
        self.assertIn("ghcr: ", body["error"])

    def test_component_tags_belong_to_their_target(self):
        self.github()
        self.jenkins()
        builds = [run(42, "api/v0.21.2"), run(41, "v0.18.0"), run(40, "web/v0.19.0")]

        with (
            mock.patch(
                "action_platform.providers.ci.jenkins.CIJenkins.runs",
                return_value=builds,
            ) as listed,
            mock.patch(
                "action_platform.providers.ci.github_actions.CIGithubActions.runs",
                return_value=[],
            ),
            mock.patch(
                "action_platform.providers.deploy.docker.DeployDocker.verify",
                return_value=False,
            ),
        ):
            body = self.client.post(f"{self.base}/sync", headers=self.h()).json()

        self.assertEqual(listed.call_args.args[0], "team/demo/publish")
        ghcr = [d for d in body["deployments"] if d["target"] == "ghcr"]
        self.assertEqual(
            [(d["version"], d["status"]) for d in ghcr], [("0.21.2", "success")]
        )
        self.assertIsNone(body["error"])

    def test_a_second_sync_updates_instead_of_duplicating(self):
        self.github()

        with (
            mock.patch(
                "action_platform.providers.ci.github_actions.CIGithubActions.runs",
                return_value=[run(1, "v2.0.0", "running")],
            ),
            mock.patch(
                "action_platform.providers.deploy.pypi.DeployPypi.verify",
                return_value=False,
            ),
        ):
            self.client.post(f"{self.base}/sync", headers=self.h())

        with (
            mock.patch(
                "action_platform.providers.ci.github_actions.CIGithubActions.runs",
                return_value=[run(1, "v2.0.0", "success")],
            ),
            mock.patch(
                "action_platform.providers.deploy.pypi.DeployPypi.verify",
                return_value=True,
            ),
        ):
            body = self.client.post(f"{self.base}/sync", headers=self.h()).json()

        pypi = [d for d in body["deployments"] if d["target"] == "pypi"]
        self.assertEqual(
            [(d["version"], d["status"]) for d in pypi], [("2.0.0", "verified")]
        )

    def test_a_deployment_links_the_ci_run_when_it_was_imported(self):
        self.github()
        from app.core.db.models import App
        from app.services.ci import CiService

        with mock.patch(
            "action_platform.providers.ci.github_actions.CIGithubActions.runs",
            return_value=[run(77, "v3.0.0")],
        ):
            with self.app.state.db.session() as s:
                CiService(s, self.app.state.sealer).sync_runs(
                    self.org["id"], s.get(App, "a1"), "acme/demo"
                )

            with mock.patch(
                "action_platform.providers.deploy.pypi.DeployPypi.verify",
                return_value=False,
            ):
                body = self.client.post(f"{self.base}/sync", headers=self.h()).json()

        pypi = [d for d in body["deployments"] if d["target"] == "pypi"][0]
        self.assertIsNotNone(pypi["ci_run_id"])

    def test_a_manual_record_needs_a_known_target_and_a_version(self):
        res = self.client.post(
            self.base,
            json={
                "target": "pypi",
                "version": "v1.0.0",
                "url": "https://pypi.org/p/demo",
            },
            headers=self.h(),
        )
        self.assertEqual(res.status_code, 201, res.text)
        self.assertEqual(
            (res.json()["executor"], res.json()["version"], res.json()["actor"]),
            ("manual", "1.0.0", "Ana"),
        )

        self.assertEqual(
            self.client.post(
                self.base, json={"target": "nope", "version": "1.0.0"}, headers=self.h()
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                self.base, json={"target": "pypi", "version": "  "}, headers=self.h()
            ).status_code,
            400,
        )

    def test_sync_without_a_source_host_reports_and_moves_on(self):
        body = self.client.post(f"{self.base}/sync", headers=self.h()).json()

        self.assertIn("pypi: ", body["error"])
        self.assertIn("no GitHub source host", body["error"])
