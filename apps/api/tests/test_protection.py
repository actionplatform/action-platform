"""Git-flow on the code host: the app's setting, applying through the host's API, the sweep that puts drift back, and who may change it."""

from __future__ import annotations

import json
import unittest
from unittest import mock

from action_platform.providers.protection.gitlab import GitlabProtection
from action_platform.testing.hosts import FakeHost, refused
from app.services.integrations.hosts.github_app import GithubApp, Installation
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

    def patch(self, name, body):
        row = self.branches[name]

        if "allow_force_push" in body:
            row["allow_force_push"] = body["allow_force_push"]

        for item in body.get("allowed_to_push") or []:
            if item.get("_destroy"):
                row["push_access_levels"] = [
                    level
                    for level in row["push_access_levels"]
                    if level["id"] != item["id"]
                ]
            else:
                row["push_access_levels"].append(
                    {"id": 99, "access_level": 40, "user_id": item.get("user_id")}
                )

        return row

    def protect(self, body):
        name = body["name"]
        levels = [{"id": 1, "access_level": body["push_access_level"], "user_id": None}]
        levels += [
            {"id": 2, "access_level": 40, "user_id": i["user_id"]}
            for i in body.get("allowed_to_push") or []
        ]
        self.branches[name] = {
            "name": name,
            "allow_force_push": body["allow_force_push"],
            "push_access_levels": levels,
        }
        path = f"{PROJECT}/protected_branches/{name}"
        self.host.routes[("GET", path)] = lambda _: self.branches[name]
        self.host.routes[("PATCH", path)] = lambda b: self.patch(name, b)

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
        self.assertTrue(
            self.client.get(BASE, headers=self.h()).json()["state"]["active"]
        )

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

    def store_app(self, key: str | None = "pem") -> None:
        from app.core.db.models import OAuthApp

        sealer = self.app.state.sealer
        with self.app.state.db.session() as s:
            s.add(
                OAuthApp(
                    provider="github",
                    client_id="Iv1.abc",
                    client_secret_encrypted=sealer.seal("secret"),
                    slug="ap-acme",
                    app_id="4242" if key else None,
                    private_key_encrypted=sealer.seal(key) if key else None,
                )
            )

    def apply(self, installation=None, token="ghs_installation"):
        from action_platform.core.flow.protection import ProtectionState

        provider = mock.Mock()
        provider.contexts.return_value = ()
        provider.apply.return_value = ProtectionState("github")
        provider.status.return_value = ProtectionState("github")

        with (
            mock.patch(
                "app.services.protection.service.build_branch_protection",
                return_value=provider,
            ) as build,
            mock.patch.object(GithubApp, "installation", return_value=installation),
            mock.patch.object(GithubApp, "token", return_value=token) as minted,
        ):
            res = self.client.post(f"{BASE}/apply", headers=self.h())

        self.assertEqual(res.status_code, 200, res.text)

        return res.json()["state"], build, minted

    def test_without_a_github_app_connection_nothing_is_applied(self):
        state, build, minted = self.apply()

        self.assertFalse(state["active"])
        self.assertIn("no GitHub App connection", state["error"])
        self.assertEqual(
            state["fix"], {"label": "Create the GitHub App", "url": "/settings"}
        )
        build.return_value.apply.assert_not_called()
        minted.assert_not_called()

    def test_an_app_without_its_private_key_asks_to_create_it_again(self):
        self.store_app(key=None)

        state, build, _ = self.apply()

        self.assertIn("private key", state["error"])
        self.assertEqual(state["fix"]["label"], "Create the GitHub App again")
        build.return_value.apply.assert_not_called()

    def test_an_app_not_installed_on_the_repository_offers_the_install(self):
        self.store_app()

        state, build, minted = self.apply(installation=None)

        self.assertIn("not installed on acme/demo", state["error"])
        self.assertEqual(
            state["fix"]["url"], "https://github.com/apps/ap-acme/installations/new"
        )
        build.return_value.apply.assert_not_called()
        minted.assert_not_called()

    def test_a_missing_permission_is_named_with_the_installation_link(self):
        self.store_app()
        installation = Installation(
            "77", "acme", True, {"administration": "read", "contents": "write"}
        )

        state, build, _ = self.apply(installation=installation)

        self.assertIn('"Administration" is read (needs write)', state["error"])
        self.assertNotIn("Contents", state["error"].split("Rulesets")[0])
        self.assertEqual(
            state["fix"]["url"],
            "https://github.com/organizations/acme/settings/installations/77",
        )
        build.return_value.apply.assert_not_called()

    def test_applies_with_the_installation_token_and_the_app_as_bypass_actor(self):
        self.store_app()
        installation = Installation(
            "77", "acme", True, {"administration": "write", "contents": "write"}
        )

        state, build, minted = self.apply(installation=installation)

        self.assertIsNone(state.get("error"))
        self.assertIsNone(state["fix"])
        self.assertEqual(
            build.call_args.args[:3], ("github", "acme/demo", "ghs_installation")
        )
        identity = build.call_args.kwargs["app"]
        self.assertEqual((identity.kind, identity.id), ("github_app", "4242"))
        policy = build.return_value.apply.call_args.args[0]
        self.assertEqual(policy.identity.id, "4242")
        minted.assert_called_once_with("acme/demo", installation)

    def release(self, state: dict):
        from app.core.db.models import App, AppProtection
        from app.schemas import ReleaseRequest, SourceCredentials
        from app.services.jobs.context import JobContext
        from app.repositories.workspace.source import get_registry
        from app.services.jobs.handlers import JobHandlers

        handlers = JobHandlers(self.app.state.db, self.app.state.sealer, get_registry())
        with self.app.state.db.session() as s:
            app = s.get(App, "a1")
            s.expunge(app)
        ctx = JobContext(None, app, {}, {"registry_id": self.registry_id})
        request = ReleaseRequest(
            level="patch",
            dry_run=False,
            credentials=SourceCredentials(kind="github", token="ghu_user"),
        )
        untouched = handlers._as_platform(ctx, request)

        with self.app.state.db.session() as s:
            s.add(AppProtection(app_id="a1", state=json.dumps(state), enforced=True))

        return untouched, handlers, ctx, request

    def test_release_on_a_protected_repository_pushes_as_the_app(self):
        self.store_app()
        installation = Installation(
            "77", "acme", True, {"administration": "write", "contents": "write"}
        )
        untouched, handlers, ctx, request = self.release({"active": True})

        with (
            mock.patch.object(GithubApp, "installation", return_value=installation),
            mock.patch.object(
                GithubApp, "token", return_value="ghs_installation"
            ) as token,
        ):
            swapped = handlers._as_platform(ctx, request)

        self.assertEqual(untouched.credentials.token, "ghu_user")
        self.assertEqual(swapped.credentials.token, "ghs_installation")
        self.assertEqual(swapped.credentials.username, "x-access-token")
        self.assertEqual(token.call_args.args[0], "acme/demo")

    def test_release_refuses_when_active_rules_and_no_app_to_push_as(self):
        from action_platform.core.exception import ProviderError

        self.store_app(key=None)
        _, handlers, ctx, request = self.release({"active": True})

        with self.assertRaisesRegex(ProviderError, "private key"):
            handlers._as_platform(ctx, request)

    def test_release_without_rules_on_the_host_keeps_the_user_token(self):
        _, handlers, ctx, request = self.release({"active": False})

        self.assertEqual(
            handlers._as_platform(ctx, request).credentials.token, "ghu_user"
        )


class GithubAppTest(unittest.TestCase):
    def app(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()

        return GithubApp("4242", pem, "ap-acme"), key.public_key()

    def test_jwt_is_signed_with_the_stored_key_and_issued_by_the_app(self):
        import base64

        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        github, public = self.app()
        header, claims, signature = github.jwt(1_000_000).split(".")
        public.verify(
            base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4)),
            f"{header}.{claims}".encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        body = json.loads(base64.urlsafe_b64decode(claims + "=" * (-len(claims) % 4)))
        self.assertEqual(body["iss"], "4242")

    def test_installation_reads_permissions_and_a_404_means_not_installed(self):
        from action_platform.core.exception import ProviderError

        github, _ = self.app()
        answer = {
            "id": 77,
            "account": {"login": "acme", "type": "Organization"},
            "permissions": {"administration": "write", "contents": "read"},
        }

        with mock.patch(
            "app.services.integrations.hosts.github_app.http.get_json",
            return_value=answer,
        ) as get:
            found = github.installation("acme/demo")

        self.assertIn("/repos/acme/demo/installation", get.call_args.args[0])
        self.assertEqual(
            found.missing({"contents": "write"}), [("contents", "write", "read")]
        )
        self.assertEqual(
            found.review_url,
            "https://github.com/organizations/acme/settings/installations/77",
        )

        with mock.patch(
            "app.services.integrations.hosts.github_app.http.get_json",
            side_effect=ProviderError("404 from api.github.com"),
        ):
            self.assertIsNone(github.installation("acme/demo"))

    def test_token_is_scoped_to_the_repository(self):
        github, _ = self.app()

        with mock.patch(
            "app.services.integrations.hosts.github_app.http.post_json",
            return_value={"token": "ghs_x"},
        ) as post:
            token = github.token("acme/demo", Installation("77", "acme", True))

        self.assertEqual(token, "ghs_x")
        self.assertTrue(
            post.call_args.args[0].endswith("/app/installations/77/access_tokens")
        )
        self.assertEqual(post.call_args.args[1], {"repositories": ["demo"]})


class StoredAppKeyTest(GateCase):
    def test_manifest_key_is_kept_sealed_and_dropped_when_another_app_is_saved(self):
        from app.core.db.models import OAuthApp
        from app.services.integrations.hosts.directory import IntegrationsDirectory

        with self.app.state.db.session() as s:
            writes = IntegrationsDirectory(s, self.app.state.sealer)
            writes.save_oauth_app(
                "github", "Iv1.a", "s", None, "ap", app_id="1", private_key="pem"
            )
            self.assertNotEqual(s.get(OAuthApp, "github").private_key_encrypted, "pem")
            self.assertEqual(writes.app_key("github").private_key, "pem")

            writes.save_oauth_app("github", "Iv1.a", "s2", None)
            self.assertEqual(writes.app_key("github").app_id, "1")

            writes.save_oauth_app("github", "Iv1.other", "s3", None)
            self.assertIsNone(writes.app_key("github"))


if __name__ == "__main__":
    unittest.main()
