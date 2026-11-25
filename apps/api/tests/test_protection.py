"""Git-flow on the code host: the app's setting, applying through the host's API, the sweep that puts drift back, and who may change it."""

from __future__ import annotations

import json
import unittest
from unittest import mock

from action_platform.providers.protection.gitlab import GitlabProtection
from action_platform.testing.hosts import FakeHost, refused
from tests.test_access import GateCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

BASE = "/api/v1/projects/p1/apps/a1/protection"
PROJECT = "/projects/acme%2Fdemo"


class GitlabHost:
    """A GitLab Premium project in memory, the way its REST API answers."""

    def __init__(self) -> None:
        self.branches: dict[str, dict] = {}
        self.project = {"only_allow_merge_if_pipeline_succeeds": False}
        self.rule = None
        self.host = FakeHost(
            {
                ("GET", "/user"): {"id": 9, "username": "ap-bot"},
                ("GET", PROJECT): lambda _: self.project,
                ("PUT", PROJECT): lambda b: self.project.update(b),
                ("POST", f"{PROJECT}/protected_branches"): self.protect,
                ("GET", f"{PROJECT}/push_rule"): lambda _: self.rule,
                ("POST", f"{PROJECT}/push_rule"): self.set_rule,
                ("PUT", f"{PROJECT}/push_rule"): self.set_rule,
            }
        )

    def set_rule(self, body):
        self.rule = dict(body)

        return self.rule

    def protect(self, body):
        name = body["name"]
        levels = [{"access_level": body["push_access_level"], "user_id": None}]
        levels += [
            {"access_level": 40, "user_id": i["user_id"]}
            for i in body.get("allowed_to_push") or []
        ]
        self.branches[name] = {
            "name": name,
            "allow_force_push": body["allow_force_push"],
            "push_access_levels": levels,
        }
        path = f"{PROJECT}/protected_branches/{name}"
        self.host.routes[("GET", path)] = lambda _: self.branches[name]
        self.host.routes[("DELETE", path)] = lambda _: self.branches.pop(name)

        return self.branches[name]

    def build(self, kind, repo, token, **_):
        assert (kind, repo, token) == ("gitlab", "acme/demo", "glpat")

        return GitlabProtection(repo, token, send=self.host)


@unittest.skipUnless(TestClient, "fastapi is not installed")
class ProtectionTest(GateCase):
    def setUp(self):
        super().setUp()
        self.registry_id = self.register()
        self.gitlab = GitlabHost()
        patcher = mock.patch(
            "app.services.protection.service.build_branch_protection",
            side_effect=self.gitlab.build,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.connect("gitlab", "glpat")
        self.configure({"source_host": {"kind": "gitlab", "repo": "acme/demo"}})

    def connect(self, kind: str, token: str) -> None:
        from app.core.db.models import App, SourceHost

        with self.app.state.db.session() as s:
            s.add(
                SourceHost(
                    id="h1",
                    organization_id=self.org["id"],
                    kind=kind,
                    name=kind,
                    auth_kind="token",
                    token_encrypted=self.app.state.sealer.seal(token),
                )
            )
            s.get(App, "a1").source_host_id = "h1"

    def configure(self, data: dict) -> None:
        from app.repositories.configuration.config_store import ConfigStore

        store = ConfigStore(self.app.state.db)
        store.set(self.registry_id, {**(store.get(self.registry_id) or {}), **data})

    def run_jobs(self) -> int:
        from app.services.jobs.worker import Worker

        return Worker(self.app.state.db, self.app.state.secrets, "test").run(once=True)

    def jobs(self, kind: str) -> list:
        from app.core.db.models import Job

        with self.app.state.db.session() as s:
            return [
                (j.status, j.run_after, json.loads(j.payload))
                for j in s.query(Job).filter(Job.kind == kind)
            ]

    def activity(self) -> list[dict]:
        return self.client.get(
            "/api/v1/projects/p1/apps/a1/activity?kind=protection", headers=self.h()
        ).json()["events"]

    def test_existing_apps_are_off_until_enabled(self):
        view = self.client.get(BASE, headers=self.h()).json()

        self.assertFalse(view["enforce"])
        self.assertEqual(view["source"], "organization")
        self.assertIsNone(view["state"])

        from app.services.protection import ProtectionSweep
        from app.services.jobs import JobQueue

        ProtectionSweep(self.app.state.db, JobQueue(self.app.state.db)).run()

        self.assertEqual(self.jobs("protection"), [])
        self.assertEqual(self.gitlab.host.calls, [])

    def test_enable_applies_through_the_host_and_records_it(self):
        res = self.client.put(BASE, json={"enforce": True}, headers=self.h())

        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue(res.json()["enforce"])
        self.assertEqual(res.json()["source"], "app")
        self.assertIsNotNone(res.json()["job_id"])

        from app.repositories.configuration.config_store import ConfigStore

        self.assertEqual(
            ConfigStore(self.app.state.db).get(self.registry_id)["gitflow"],
            {"protection": {"enforce": True}},
        )

        self.run_jobs()

        view = self.client.get(BASE, headers=self.h()).json()
        state = view["state"]
        self.assertTrue(state["active"], state)
        self.assertEqual(state["branches"], ["main"])
        self.assertEqual(state["bypass"], "ap-bot")
        self.assertIsNotNone(view["applied_at"])
        self.assertEqual(
            self.gitlab.branches["main"]["push_access_levels"][1]["user_id"], 9
        )
        modes = {r["rule"]: r["mode"] for r in state["rules"]}
        self.assertEqual(modes["direct_push"], "native")
        self.assertEqual(modes["branch_names"], "native")
        self.assertEqual(modes["required_checks"], "inactive")
        titles = [e["title"] for e in self.activity()]
        self.assertIn("Branch protection applied", titles)
        self.assertIn("Branch protection enforced", titles)

    def test_the_sweep_puts_drift_back_and_says_who_changed_what(self):
        self.client.put(BASE, json={"enforce": True}, headers=self.h())
        self.run_jobs()
        self.gitlab.branches["main"]["allow_force_push"] = True

        from app.services.jobs import JobQueue
        from app.services.protection import ProtectionSweep

        result = ProtectionSweep(self.app.state.db, JobQueue(self.app.state.db)).run()
        self.assertEqual(result, {"apps": 1})
        self.run_jobs()

        self.assertFalse(self.gitlab.branches["main"]["allow_force_push"])
        events = self.activity()
        drift = next(e for e in events if e["status"] == "drift")
        self.assertIn("main allows force push", drift["detail"])
        self.assertEqual(events[0]["status"], "applied")
        waiting = [j for j in self.jobs("protection_sweep") if j[0] == "queued"]
        self.assertEqual(len(waiting), 1)

    def test_a_refusal_is_shown_never_claimed(self):
        self.gitlab.host.routes[("POST", f"{PROJECT}/protected_branches")] = refused(
            403, "403 Forbidden"
        )

        res = self.client.post(f"{BASE}/apply", headers=self.h())

        state = res.json()["state"]
        self.assertFalse(state["active"])
        self.assertIn("Maintainer", state["error"])
        self.assertTrue(all(r["mode"] == "inactive" for r in state["rules"]))
        self.assertEqual(self.activity()[0]["status"], "failed")

    def test_viewers_read_but_cannot_change(self):
        from app.core.db.models import Member

        with self.app.state.db.session() as s:
            s.query(Member).update({"role": "viewer"})

        self.assertEqual(self.client.get(BASE, headers=self.h()).status_code, 200)
        self.assertEqual(
            self.client.put(BASE, json={"enforce": True}, headers=self.h()).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(f"{BASE}/apply", headers=self.h()).status_code, 403
        )
        self.assertEqual(
            self.client.put(
                "/api/v1/settings/protection", json={"enforce": True}, headers=self.h()
            ).status_code,
            403,
        )
        self.assertEqual(self.gitlab.host.calls, [])

    def test_organization_default_covers_apps_without_a_setting(self):
        res = self.client.put(
            "/api/v1/settings/protection", json={"enforce": True}, headers=self.h()
        )
        self.assertEqual(res.json(), {"enforce": True})

        view = self.client.get(BASE, headers=self.h()).json()
        self.assertTrue(view["enforce"])
        self.assertEqual(view["source"], "organization")

        self.run_jobs()
        self.assertTrue(self.client.get(BASE, headers=self.h()).json()["state"]["active"])

        self.client.put(BASE, json={"enforce": False}, headers=self.h())
        self.assertFalse(self.client.get(BASE, headers=self.h()).json()["enforce"])


@unittest.skipUnless(TestClient, "fastapi is not installed")
class GithubProtectionTest(GateCase):
    def setUp(self):
        super().setUp()
        from app.core.db.models import App, SourceHost
        from app.repositories.configuration.config_store import ConfigStore

        self.registry_id = self.register()
        with self.app.state.db.session() as s:
            s.add(
                SourceHost(
                    id="h1",
                    organization_id=self.org["id"],
                    kind="github",
                    name="GitHub",
                    auth_kind="token",
                    token_encrypted=self.app.state.sealer.seal("ghu_user"),
                )
            )
            s.get(App, "a1").source_host_id = "h1"
        ConfigStore(self.app.state.db).set(
            self.registry_id, {"source_host": {"kind": "github", "repo": "acme/demo"}}
        )

    def test_without_the_app_key_nothing_reaches_github(self):
        self.setenv("AP_GITHUB_APP_ID", "")
        self.setenv("AP_GITHUB_APP_PRIVATE_KEY", "")

        with mock.patch("action_platform.providers.protection.http.rest.call") as call:
            res = self.client.post(f"{BASE}/apply", headers=self.h())

        state = res.json()["state"]
        self.assertFalse(state["active"])
        self.assertIn("AP_GITHUB_APP_PRIVATE_KEY", state["error"])
        self.assertEqual(call.call_count, 0)

    def test_release_on_a_protected_repository_pushes_as_the_app(self):
        from app.core.db.models import App, AppProtection
        from app.schemas import ReleaseRequest, SourceCredentials
        from app.services.jobs.context import JobContext
        from app.repositories.workspace.source import get_registry
        from app.services.jobs.handlers import JobHandlers

        self.setenv("AP_GITHUB_APP_ID", "4242")
        self.setenv("AP_GITHUB_APP_PRIVATE_KEY", "pem")
        handlers = JobHandlers(
            self.app.state.db, self.app.state.sealer, get_registry()
        )
        with self.app.state.db.session() as s:
            app = s.get(App, "a1")
            s.expunge(app)
        ctx = JobContext(None, app, {}, {"registry_id": self.registry_id})
        request = ReleaseRequest(
            level="patch",
            dry_run=False,
            credentials=SourceCredentials(kind="github", token="ghu_user"),
        )

        with mock.patch(
            "app.services.integrations.hosts.github_app_key.GithubAppKey.token",
            return_value="ghs_installation",
        ) as token:
            untouched = handlers._as_platform(ctx, request)

            with self.app.state.db.session() as s:
                s.add(
                    AppProtection(
                        app_id="a1", state=json.dumps({"active": True}), enforced=True
                    )
                )

            swapped = handlers._as_platform(ctx, request)

        self.assertEqual(untouched.credentials.token, "ghu_user")
        self.assertEqual(swapped.credentials.token, "ghs_installation")
        self.assertEqual(swapped.credentials.username, "x-access-token")
        self.assertEqual(token.call_args.args[0], "acme/demo")


if __name__ == "__main__":
    unittest.main()
