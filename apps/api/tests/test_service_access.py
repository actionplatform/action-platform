"""`/api/v1/access/*`: access on the services the bundled plugins own, for the caller's organization, with its plugin options."""

from __future__ import annotations

from unittest import mock

from action_platform.abc import Option, Plugin
from action_platform.core.service_access import AccessError, Grant
from action_platform.plugins import registry
from action_platform.testing.access import MemoryProvider
from tests.test_access import GateCase


class Vault(Plugin):
    slug = "vault"
    options = [
        Option("url", "URL", "url"),
        Option("token", "Token", "secret"),
    ]
    service = MemoryProvider("vault")
    seen: list = []

    def access(self, options):
        if not options.get("url"):
            return None

        if not options.get("token"):
            raise AccessError("vault: set token")

        Vault.seen.append(options.get("token"))

        return Vault.service


class ServiceAccessApiTest(GateCase):
    def setUp(self):
        super().setUp()
        registry.reset()
        self.addCleanup(registry.reset)
        loaded = registry.Loaded(Vault(), "apx-vault", "0.1.0")
        patcher = mock.patch.object(
            registry.Plugins, "find", staticmethod(lambda known=None: [loaded])
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        Vault.service = MemoryProvider("vault")
        Vault.service.add("ana@example.com", "org", "admin")
        Vault.service.add("bot", "org", "admin")
        Vault.seen = []

    def configure(self, options):
        self.client.put(
            "/api/v1/plugins/vault/options",
            json={"options": options},
            headers=self.h(),
        )

    def test_nothing_configured_says_so(self):
        answer = self.client.get("/api/v1/access/audit", headers=self.h())

        self.assertEqual(answer.status_code, 400)
        self.assertIn("no service to manage", answer.json()["detail"])

    def test_an_incomplete_configuration_shows_as_a_failed_service(self):
        self.configure({"url": "https://v.test"})

        rows = self.client.get("/api/v1/access/audit", headers=self.h()).json()

        self.assertEqual(
            [(r["service"], r["ok"], r["error"]) for r in rows["services"]],
            [("vault", False, "vault: set token")],
        )

    def test_first_sync_imports_with_the_sealed_secret_and_changes_nothing(self):
        self.configure({"url": "https://v.test", "token": "tok-1"})

        dry = self.client.post("/api/v1/access/sync", json={}, headers=self.h()).json()

        self.assertTrue(dry["bootstrap"] and dry["dry_run"])
        self.assertEqual(Vault.seen, ["tok-1"])

        stored = self.client.post(
            "/api/v1/access/sync", json={"apply": True}, headers=self.h()
        ).json()

        self.assertEqual((stored["imported"], stored["changes"]), (["vault"], []))
        self.assertEqual(Vault.service.applied, [])

        audit = self.client.get("/api/v1/access/audit", headers=self.h()).json()
        row = audit["services"][0]

        self.assertEqual(audit["organization_members"], 1)
        self.assertEqual((row["imported"], row["drift"]), (True, []))
        self.assertEqual(row["outside_accounts"], ["bot"])
        self.assertEqual(row["levels"]["org"], ["member", "admin"])

        who = self.client.get(
            "/api/v1/access/who?person=ana@example.com", headers=self.h()
        ).json()

        self.assertEqual(who["person"]["accounts"], {"vault": "ana@example.com"})

    def test_grant_and_offboard_change_the_service_only_with_apply(self):
        self.configure({"url": "https://v.test", "token": "tok-1"})
        self.client.post("/api/v1/access/sync", json={"apply": True}, headers=self.h())

        plan = self.client.post(
            "/api/v1/access/grant",
            json={
                "person": "ana@example.com",
                "service": "vault",
                "resource": "repo/api",
                "level": "write",
            },
            headers=self.h(),
        ).json()

        self.assertEqual(
            [(c["resource"], c["status"]) for c in plan["changes"]],
            [("repo/api", "planned")],
        )
        self.assertEqual(Vault.service.applied, [])

        self.client.post(
            "/api/v1/access/grant",
            json={
                "person": "ana@example.com",
                "service": "vault",
                "resource": "repo/api",
                "level": "write",
                "apply": True,
            },
            headers=self.h(),
        )

        self.assertIn(
            Grant("vault", "ana@example.com", "repo/api", "write"),
            Vault.service.grants,
        )

        gone = self.client.post(
            "/api/v1/access/offboard",
            json={"person": "ana@example.com", "apply": True},
            headers=self.h(),
        ).json()

        self.assertEqual(
            sorted((c["resource"], c["status"]) for c in gone["changes"]),
            [("org", "applied"), ("repo/api", "applied")],
        )

    def test_every_route_needs_org_manage(self):
        self.configure({"url": "https://v.test", "token": "tok-1"})
        token = self.token("read,write,release")

        for method, path in (
            ("GET", "audit"),
            ("GET", "who?person=ana@example.com"),
            ("POST", "sync"),
            ("POST", "offboard"),
        ):
            with self.subTest(path=path):
                answer = self.client.request(
                    method,
                    f"/api/v1/access/{path}",
                    json={"person": "ana@example.com"} if method == "POST" else None,
                    headers=self.h(token),
                )

                self.assertEqual(answer.status_code, 403)

    def test_offboarding_the_last_owner_from_the_platform_changes_nothing(self):
        self.configure({"url": "https://v.test", "token": "tok-1"})
        self.client.post("/api/v1/access/sync", json={"apply": True}, headers=self.h())

        refused = self.client.post(
            "/api/v1/access/offboard",
            json={
                "person": "ana@example.com",
                "apply": True,
                "remove_from_platform": True,
            },
            headers=self.h(),
        )

        self.assertEqual(refused.status_code, 400)
        self.assertIn("at least one owner", refused.json()["detail"])
        self.assertEqual(Vault.service.applied, [])
