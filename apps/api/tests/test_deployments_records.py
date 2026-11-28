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
    number: int,
    branch: str,
    status: str = "success",
    started: datetime | None = None,
    params: dict[str, str] | None = None,
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
        params=params or {},
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

    def test_the_app_ci_server_is_a_runner_with_its_own_credentials(self):
        from app.core.db.models import App
        from app.services.deployments import AppCiRunners

        with self.app.state.db.session() as s:
            self.assertEqual(
                AppCiRunners(s, self.app.state.sealer).of_registry(self.registry_id),
                [],
            )

        self.jenkins()

        with self.app.state.db.session() as s:
            runners = AppCiRunners(s, self.app.state.sealer).of_registry(
                self.registry_id
            )
            self.assertEqual(
                [(r.name, r.base_url, r.username, r.token) for r in runners],
                [("jenkins", "https://ci.acme.io", "u", "t")],
            )
            self.assertEqual(
                AppCiRunners(s, self.app.state.sealer).of(s.get(App, "a1"))[0].name,
                "jenkins",
            )

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

    def test_one_run_records_each_target_on_its_own_stage(self):
        from app.core.db.models import App
        from app.repositories.configuration.config_store import ConfigStore
        from app.services.deployments import DeploymentRecords

        with self.app.state.db.session() as s:
            rows = DeploymentRecords(s, self.app.state.sealer).record_platform(
                s.get(App, "a1"),
                ConfigStore(self.app.state.db).config_of(self.registry_id),
                [
                    DeployResult(ok=True, target="lambda", version="1.2.0"),
                    DeployResult(
                        ok=True, target="ghcr", version="1.2.0", stage="prod-container"
                    ),
                ],
                "prod",
                "job-2",
                "Ana",
                datetime(2026, 9, 17, 9, 0),
            )

            self.assertEqual(
                [(r.target, r.stage) for r in rows],
                [("lambda", "prod"), ("ghcr", "prod-container")],
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
                "tests.support.ServerRunner.runs",
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

    def test_jenkins_builds_of_a_branch_take_version_and_scope_from_parameters(self):
        from app.repositories.configuration.config_store import ConfigStore

        ConfigStore(self.app.state.db).set(
            self.registry_id,
            {
                "project": {"name": "demo"},
                "deploy": {
                    "targets": [
                        {
                            "name": "app",
                            "kind": "docker",
                            "run_by": "jenkins",
                            "job": "team/app-prod",
                            "image": "ghcr.io/acme/app",
                            "stages": ["prod"],
                            "version_parameter": "RELEASE_TAG",
                        },
                        {
                            "name": "app-any",
                            "kind": "docker",
                            "run_by": "jenkins",
                            "job": "team/app",
                            "image": "ghcr.io/acme/app",
                            "version_parameter": "RELEASE_TAG",
                            "stage_parameter": "ENV",
                        },
                    ]
                },
            },
        )
        self.jenkins()
        builds = {
            "team/app-prod": [
                run(12, "main", params={"RELEASE_TAG": "v1.4.0"}),
                run(11, "main", params={}),
            ],
            "team/app": [
                run(5, "main", params={"RELEASE_TAG": "1.3.0", "ENV": "dev"}),
                run(4, "main", params={"RELEASE_TAG": "v1.2.0"}),
            ],
        }

        with (
            mock.patch(
                "tests.support.ServerRunner.runs",
                side_effect=lambda job, limit=50: builds[job],
            ),
            mock.patch(
                "action_platform.providers.deploy.docker.DeployDocker.verify",
                return_value=False,
            ),
        ):
            body = self.client.post(f"{self.base}/sync", headers=self.h()).json()

        self.assertIsNone(body["error"])
        self.assertEqual(
            sorted(
                (d["target"], d["version"], d["stage"], d["executor"])
                for d in body["deployments"]
            ),
            [
                ("app", "1.4.0", "prod", "jenkins"),
                ("app-any", "1.2.0", None, "jenkins"),
                ("app-any", "1.3.0", "dev", "jenkins"),
            ],
        )

    def _two_stage_targets(self):
        from app.repositories.configuration.config_store import ConfigStore

        ConfigStore(self.app.state.db).set(
            self.registry_id,
            {
                "project": {"name": "demo"},
                "deploy": {
                    "targets": [
                        {
                            "name": f"lambda-{stage}",
                            "kind": "docker",
                            "run_by": "jenkins",
                            "job": "team/app",
                            "image": "ghcr.io/acme/app",
                            "stages": [stage],
                            "version_parameter": "RELEASE_TAG",
                            "stage_parameter": "STAGE",
                        }
                        for stage in ("dev", "prod")
                    ]
                },
            },
        )
        self.jenkins()

    def _sync(self, builds):
        with (
            mock.patch(
                "tests.support.ServerRunner.runs",
                return_value=builds,
            ),
            mock.patch(
                "action_platform.providers.deploy.docker.DeployDocker.verify",
                return_value=False,
            ),
        ):
            return self.client.post(f"{self.base}/sync", headers=self.h()).json()

    def test_a_run_is_recorded_only_on_the_target_serving_its_stage(self):
        self._two_stage_targets()
        body = self._sync(
            [
                run(3, "main", params={"RELEASE_TAG": "1.0.0", "STAGE": "prod"}),
                run(2, "main", params={"RELEASE_TAG": "1.0.0", "STAGE": "dev"}),
                run(1, "main", params={"RELEASE_TAG": "0.9.0", "STAGE": "dev"}),
            ]
        )

        self.assertEqual(
            sorted(
                (d["target"], d["version"], d["stage"]) for d in body["deployments"]
            ),
            [
                ("lambda-dev", "0.9.0", "dev"),
                ("lambda-dev", "1.0.0", "dev"),
                ("lambda-prod", "1.0.0", "prod"),
            ],
        )

    def test_the_next_sync_drops_rows_recorded_for_a_stage_the_target_does_not_serve(
        self,
    ):
        from app.core.db.models import Deployment

        self._two_stage_targets()
        builds = [run(2, "main", params={"RELEASE_TAG": "1.0.0", "STAGE": "dev"})]
        self._sync(builds)

        with self.app.state.db.session() as s:
            s.add(
                Deployment(
                    id="dup",
                    app_id="a1",
                    target="lambda-prod",
                    kind="docker",
                    executor="jenkins",
                    external_ref="jenkins:2",
                    stage="dev",
                    version="1.0.0",
                    status="success",
                )
            )

        body = self._sync(builds)

        self.assertEqual(
            [(d["target"], d["stage"]) for d in body["deployments"]],
            [("lambda-dev", "dev")],
        )

    def test_a_run_the_platform_recorded_drops_its_observed_copy(self):
        from app.core.db.models import Deployment
        from app.repositories.configuration.config_store import ConfigStore

        ConfigStore(self.app.state.db).set(
            self.registry_id,
            {
                "project": {"name": "demo"},
                "deploy": {
                    "targets": [
                        {
                            "name": "lambda-dev",
                            "kind": "docker",
                            "run_by": "jenkins",
                            "job": "team/app",
                            "image": "ghcr.io/acme/app",
                            "stages": ["dev"],
                            "observe": False,
                            "version_parameter": "RELEASE_TAG",
                        }
                    ]
                },
            },
        )
        self.jenkins()

        with self.app.state.db.session() as s:
            s.add_all(
                [
                    Deployment(
                        id="shipped",
                        app_id="a1",
                        target="lambda-dev",
                        kind="docker",
                        executor="platform",
                        external_ref="job-1",
                        stage="dev",
                        version="1.0.0",
                        status="success",
                    ),
                    Deployment(
                        id="stale",
                        app_id="a1",
                        target="lambda-dev",
                        kind="docker",
                        executor="jenkins",
                        external_ref="jenkins:2",
                        stage="dev",
                        version="1.0.0",
                        status="running",
                    ),
                ]
            )

        body = self._sync([run(2, "main", params={"RELEASE_TAG": "v1.0.0"})])

        self.assertEqual(
            [(d["id"], d["status"]) for d in body["deployments"]],
            [("shipped", "success")],
        )

    def test_an_observed_ci_target_is_imported_on_sync(self):
        from app.repositories.configuration.config_store import ConfigStore

        ConfigStore(self.app.state.db).set(
            self.registry_id,
            {
                "project": {"name": "demo"},
                "deploy": {
                    "targets": [
                        {
                            "name": "pypi",
                            "kind": "pypi",
                            "run_by": "github_actions",
                            "observe": True,
                            "workflow": "publish.yml",
                            "package": "demo",
                        }
                    ]
                },
            },
        )
        self.github()

        with (
            mock.patch(
                "action_platform.providers.ci.github_actions.CIGithubActions.runs",
                return_value=[run(3, "v1.0.0"), run(2, "main")],
            ),
            mock.patch(
                "action_platform.providers.deploy.pypi.DeployPypi.verify",
                return_value=True,
            ),
        ):
            body = self.client.post(f"{self.base}/sync", headers=self.h()).json()

        self.assertIsNone(body["error"])
        self.assertEqual(
            [(d["version"], d["status"], d["executor"]) for d in body["deployments"]],
            [("1.0.0", "verified", "github_actions")],
        )

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

    def test_a_deployment_never_links_a_run_of_another_job(self):
        self.github()
        from app.core.db.models import App
        from app.services.ci import CiService

        other = run(77, "main")
        other.url = "https://ci/other-job/77"

        with mock.patch(
            "action_platform.providers.ci.github_actions.CIGithubActions.runs",
            return_value=[other],
        ):
            with self.app.state.db.session() as s:
                CiService(s, self.app.state.sealer).sync_runs(
                    self.org["id"], s.get(App, "a1"), "acme/demo"
                )

        with mock.patch(
            "action_platform.providers.ci.github_actions.CIGithubActions.runs",
            return_value=[run(77, "v3.0.0")],
        ):
            with mock.patch(
                "action_platform.providers.deploy.pypi.DeployPypi.verify",
                return_value=False,
            ):
                body = self.client.post(f"{self.base}/sync", headers=self.h()).json()

        pypi = [d for d in body["deployments"] if d["target"] == "pypi"][0]
        self.assertIsNone(pypi["ci_run_id"])

    def test_deployments_come_in_pages_when_asked(self):
        for version in ("1.0.0", "1.1.0", "1.2.0"):
            res = self.client.post(
                self.base,
                json={"target": "pypi", "version": version},
                headers=self.h(),
            )
            self.assertEqual(res.status_code, 201, res.text)

        whole = self.client.get(self.base, headers=self.h()).json()
        paged = self.client.get(f"{self.base}?page=2&per=2", headers=self.h()).json()

        self.assertNotIn("total", whole)
        self.assertEqual(len(whole["deployments"]), 3)
        self.assertEqual((paged["total"], paged["page"], paged["per"]), (3, 2, 2))
        self.assertEqual(paged["deployments"], whole["deployments"][2:])
        self.assertEqual(paged["targets"], whole["targets"])

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
