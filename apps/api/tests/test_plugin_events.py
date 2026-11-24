"""Events on the hosted platform: one delivery per plugin and route, the same from every executor, retried by the queue, read back by the organization's admins."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from action_platform.abc import Option, Plugin
from action_platform.core.context import Check, DeployResult
from action_platform.core.exception import ActionPlatformError
from action_platform.plugins import registry
from tests.test_access import GateCase
from tests.test_deployments_records import TARGETS, run

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


class Chat(Plugin):
    slug = "chat"
    options = [
        Option("hook", "Webhook", "secret"),
        Option("events", "Events"),
    ]

    def __init__(self) -> None:
        self.sent: list = []
        self.fail: Exception | None = None

    def routes(self, event, options) -> list[str]:
        wanted = (options.get("events") or "").split(",")

        if not options.get("hook") or (wanted != [""] and event.kind not in wanted):
            return []

        return ["chat", "chat"]

    def deliver(self, event, route, options) -> None:
        if self.fail is not None:
            raise self.fail

        self.sent.append((event, route, options.get("hook")))


def recent(seconds: int = 0) -> datetime:
    return (
        datetime.now(timezone.utc) - timedelta(minutes=5) + timedelta(seconds=seconds)
    )


@unittest.skipUnless(TestClient, "fastapi is not installed")
class PluginEventsTest(GateCase):
    def setUp(self):
        super().setUp()
        from app.repositories.configuration.config_store import ConfigStore

        self.setenv("AP_PUBLIC_URL", "https://ap.example.com")
        registry.reset()
        self.addCleanup(registry.reset)
        self.chat = Chat()
        loaded = registry.Loaded(self.chat, "apx-chat", "0.1.0")
        patcher = mock.patch.object(
            registry.Plugins, "find", staticmethod(lambda known=None: [loaded])
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.registry_id = self.register()
        ConfigStore(self.app.state.db).set(
            self.registry_id, {"project": {"name": "demo"}, "deploy": TARGETS}
        )
        self.configure({"hook": "https://hooks.test/T0/B0/abc"})

    def configure(self, options: dict) -> None:
        res = self.client.put(
            "/api/v1/plugins/chat/options", json={"options": options}, headers=self.h()
        )
        self.assertEqual(res.status_code, 200, res.text)

    def queued(self) -> list[dict]:
        from sqlalchemy import select

        from app.core.db.models import Job

        with self.app.state.db.session() as s:
            return [
                {**json.loads(j.payload), "status": j.status, "org": j.organization_id}
                for j in s.scalars(
                    select(Job)
                    .where(Job.kind == "plugin_event")
                    .order_by(Job.created_at)
                )
            ]

    def shipped(self, ok: bool = True) -> None:
        from app.core.db.models import App
        from app.repositories.configuration.config_store import ConfigStore
        from app.services.deployments import DeploymentRecords

        with self.app.state.db.session() as s:
            DeploymentRecords(s, self.app.state.sealer).record_platform(
                s.get(App, "a1"),
                ConfigStore(self.app.state.db).config_of(self.registry_id),
                [DeployResult(ok=ok, target="lambda", version="1.2.0")],
                "prod",
                "job-1",
                "Ana",
                recent().replace(tzinfo=None),
            )

    def jenkins(self) -> None:
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

    def test_a_platform_deploy_queues_one_delivery_per_route_with_the_envelope(self):
        self.shipped()

        jobs = self.queued()

        self.assertEqual(len(jobs), 1)
        self.assertEqual(
            (jobs[0]["plugin"], jobs[0]["route"], jobs[0]["org"]),
            ("chat", "chat", self.org["id"]),
        )
        event = jobs[0]["event"]
        self.assertEqual(
            (event["kind"], event["organization"], event["project"], event["app"]),
            ("deployment.succeeded", "acme", "web", "demo"),
        )
        self.assertEqual(event["actor"], "Ana")
        self.assertEqual(
            (event["payload"]["stage"], event["payload"]["version"]), ("prod", "1.2.0")
        )
        self.assertEqual(
            event["url"], "https://ap.example.com/projects/p1/apps/a1/deployments"
        )
        self.assertNotIn("hooks.test", json.dumps(jobs))

    def test_a_failed_deploy_is_its_own_event(self):
        self.shipped(ok=False)

        self.assertEqual(
            [j["event"]["kind"] for j in self.queued()], ["deployment.failed"]
        )

    def test_a_jenkins_observed_deploy_raises_the_same_event(self):
        self.jenkins()

        with (
            mock.patch(
                "action_platform.providers.ci.jenkins.CIJenkins.runs",
                return_value=[run(42, "api/v0.21.2", started=recent())],
            ),
            mock.patch(
                "action_platform.providers.ci.github_actions.CIGithubActions.runs",
                return_value=[],
            ),
            mock.patch(
                "action_platform.providers.deploy.docker.DeployDocker.verify",
                return_value=False,
            ),
        ):
            self.client.post(
                "/api/v1/projects/p1/apps/a1/deployments/sync", headers=self.h()
            )
            self.client.post(
                "/api/v1/projects/p1/apps/a1/deployments/sync", headers=self.h()
            )

        events = [j["event"] for j in self.queued()]
        self.assertEqual(
            [(e["kind"], e["payload"]["executor"]) for e in events],
            [("deployment.succeeded", "jenkins")],
        )
        self.assertEqual(events[0]["payload"]["version"], "0.21.2")

    def test_a_verified_observed_deploy_is_announced_once_per_state(self):
        self.jenkins()
        self.configure(
            {
                "hook": "https://hooks.test/x",
                "events": "deployment.succeeded,deployment.verified",
            }
        )

        with (
            mock.patch(
                "action_platform.providers.ci.jenkins.CIJenkins.runs",
                return_value=[run(42, "api/v0.21.2", started=recent())],
            ),
            mock.patch(
                "action_platform.providers.ci.github_actions.CIGithubActions.runs",
                return_value=[],
            ),
            mock.patch(
                "action_platform.providers.deploy.docker.DeployDocker.verify",
                return_value=True,
            ),
        ):
            for _ in range(2):
                body = self.client.post(
                    "/api/v1/projects/p1/apps/a1/deployments/sync", headers=self.h()
                ).json()

        self.assertEqual(
            [j["event"]["kind"] for j in self.queued()],
            ["deployment.succeeded", "deployment.verified"],
        )
        self.assertEqual(
            [d["status"] for d in body["deployments"] if d["target"] == "ghcr"],
            ["verified"],
        )

    def test_history_older_than_a_day_is_not_news(self):
        self.jenkins()
        old = datetime.now(timezone.utc) - timedelta(days=3)

        with (
            mock.patch(
                "action_platform.providers.ci.jenkins.CIJenkins.runs",
                return_value=[run(42, "api/v0.21.2", started=old)],
            ),
            mock.patch(
                "action_platform.providers.ci.github_actions.CIGithubActions.runs",
                return_value=[],
            ),
            mock.patch(
                "action_platform.providers.deploy.docker.DeployDocker.verify",
                return_value=True,
            ),
        ):
            body = self.client.post(
                "/api/v1/projects/p1/apps/a1/deployments/sync", headers=self.h()
            ).json()

        self.assertEqual(
            [d["status"] for d in body["deployments"] if d["target"] == "ghcr"],
            ["verified"],
        )
        self.assertEqual(self.queued(), [])

    def test_a_plugin_whose_options_route_nothing_gets_nothing(self):
        self.configure({"hook": None, "events": "release.created"})
        self.shipped()

        self.configure({"hook": "https://hooks.test/x", "events": "release.created"})
        self.shipped(ok=False)

        self.assertEqual(self.queued(), [])

    def handlers(self):
        from app.repositories.workspace.source import get_registry
        from app.services.jobs.handlers import JobHandlers

        return JobHandlers(self.app.state.db, self.app.state.sealer, get_registry())

    def payload(self, action: str, body: dict) -> dict:
        return {
            "path": f"apps/{self.registry_id}/{action}",
            "method": "POST",
            "body": body,
            "registry_id": self.registry_id,
            "organization_id": self.org["id"],
            "app_id": "a1",
            "job_id": "j1",
            "user_id": self.user_id,
        }

    def test_a_readiness_verdict_that_turns_blocked_is_an_event_once(self):
        from app.services.releases import ReleaseStore
        from app.services.releases.readiness import ReadinessService

        with self.app.state.db.session() as s:
            ReleaseStore(s).ensure("a1", "v1.2.0", "platform")

        blocked = [Check("aws.permissions", False, "denied", fix="grant it")]
        body = {"tag": "v1.2.0", "stage": "prod"}

        with mock.patch.object(ReadinessService, "check", return_value=blocked):
            self.handlers().readiness(self.payload("readiness", body))
            self.handlers().readiness(self.payload("readiness", body))

        events = [j["event"] for j in self.queued()]
        self.assertEqual([e["kind"] for e in events], ["readiness.blocked"])
        self.assertEqual(
            events[0]["payload"]["checks"],
            [{"id": "aws.permissions", "detail": "denied", "fix": "grant it"}],
        )
        self.assertEqual(
            events[0]["url"],
            "https://ap.example.com/projects/p1/apps/a1/releases/v1.2.0",
        )

    def test_a_release_cut_here_is_an_event(self):
        from app.services.jobs.handlers import JobHandlers
        from app.services.releases import ReleasesService

        with (
            mock.patch.object(
                ReleasesService,
                "release",
                return_value={"current": "1.2.3", "next": "1.3.0", "changelog": "- x"},
            ),
            mock.patch.object(JobHandlers, "import_activity", return_value={}),
            mock.patch.object(JobHandlers, "_snapshot"),
        ):
            self.handlers().release(
                self.payload("release", {"level": "minor", "dry_run": False})
            )

        events = [j["event"] for j in self.queued()]
        self.assertEqual(
            [(e["kind"], e["payload"]["tag"], e["actor"]) for e in events],
            [("release.created", "v1.3.0", "Ana")],
        )
        self.assertEqual(events[0]["payload"]["changelog"], "- x")

    def test_a_failed_ci_run_on_a_release_tag_is_an_event_a_branch_is_not(self):
        from action_platform.core.context import Run
        from app.services.releases import ReleaseStore

        with self.app.state.db.session() as s:
            ReleaseStore(s).ensure("a1", "v1.3.0", "platform")

        self.jenkins()
        self.client.put(
            "/api/v1/projects/p1/apps/a1/ci",
            json={"ci_host_id": self.ci_host(), "job": "team/app/main"},
            headers=self.h(),
        )
        runs = [
            Run(number=8, status="failure", branch="v1.3.0", started_at=recent()),
            Run(number=7, status="failure", branch="main", started_at=recent()),
        ]

        for _ in range(2):
            with mock.patch(
                "action_platform.providers.ci.jenkins.CIJenkins.runs",
                return_value=runs,
            ):
                self.client.post(
                    "/api/v1/projects/p1/apps/a1/ci/sync", headers=self.h()
                )

        events = [j["event"] for j in self.queued()]
        self.assertEqual(
            [(e["kind"], e["payload"]["tag"], e["payload"]["run"]) for e in events],
            [("ci.failed", "v1.3.0", 8)],
        )

    def ci_host(self) -> str:
        from app.core.db.models import App

        with self.app.state.db.session() as s:
            return s.get(App, "a1").ci_host_id

    def test_the_worker_delivers_with_the_secret_opened(self):
        from app.services.jobs.worker import Worker

        self.shipped()
        Worker(self.app.state.db, self.app.state.secrets, "test").run(
            once=True, kinds=["plugin_event"]
        )

        self.assertEqual(len(self.chat.sent), 1)
        event, route, hook = self.chat.sent[0]
        self.assertEqual(
            (event.kind, route, hook),
            ("deployment.succeeded", "chat", "https://hooks.test/T0/B0/abc"),
        )
        self.assertEqual([j["status"] for j in self.queued()], ["done"])

    def test_a_server_error_is_retried_and_a_refusal_is_not(self):
        from app.services.jobs.worker import Worker

        self.shipped()
        self.chat.fail = RuntimeError("502 from hooks")
        worker = Worker(self.app.state.db, self.app.state.secrets, "test")
        worker.run(once=True, kinds=["plugin_event"])

        self.assertEqual([j["status"] for j in self.queued()], ["queued"])

        self.shipped(ok=False)
        self.chat.fail = ActionPlatformError("chat: 404 from the webhook")
        worker.run(once=True, kinds=["plugin_event"])

        self.assertEqual([j["status"] for j in self.queued()], ["queued", "failed"])

    def test_deliveries_are_listed_for_the_organizations_admins(self):
        from app.services.jobs.worker import Worker

        self.shipped()
        Worker(self.app.state.db, self.app.state.secrets, "test").run(
            once=True, kinds=["plugin_event"]
        )

        res = self.client.get("/api/v1/plugins/chat/deliveries", headers=self.h())

        self.assertEqual(res.status_code, 200, res.text)
        rows = res.json()["deliveries"]
        self.assertEqual(
            [
                (r["event"], r["route"], r["project"], r["app"], r["status"])
                for r in rows
            ],
            [("deployment.succeeded", "chat", "web", "demo", "done")],
        )
        self.assertNotIn("hooks.test", res.text)
        self.assertEqual(
            self.client.get(
                "/api/v1/plugins/other/deliveries", headers=self.h()
            ).json(),
            {"deliveries": []},
        )

    def test_the_catalog_says_which_plugins_take_events(self):
        rows = self.client.get("/api/v1/plugins", headers=self.h()).json()["plugins"]

        self.assertEqual([(r["slug"], r["events"]) for r in rows], [("chat", True)])
