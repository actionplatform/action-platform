"""Connections a plugin reads instead of a pasted token: Connect Sentry (OAuth, refreshed, sealed), the organization's GitHub host, and only for the kinds a plugin declares."""

from __future__ import annotations

from datetime import timedelta
from unittest import mock

from action_platform.abc import Connection, Plugin
from action_platform.core.service_access import AccessError
from action_platform.plugins import registry
from action_platform.testing.access import MemoryProvider
from tests.test_access import GateCase


class Watcher(Plugin):
    slug = "watcher"
    connections = [
        Connection("sentry", ("member:admin", "team:write")),
        Connection("github", ("admin:org",), (("members", "write"),)),
    ]
    seen: list = []

    def access(self, options):
        if not options.get("org"):
            return None

        found = options.credential("sentry")
        Watcher.seen.append((found, options.credential("github")))

        if found is None:
            raise AccessError("watcher: connect Sentry")

        return MemoryProvider("watcher")


class Stranger(Plugin):
    slug = "stranger"
    seen: list = []

    def access(self, options):
        Stranger.seen.append(options.credential("sentry"))

        return None


class ConnectionsTest(GateCase):
    def setUp(self):
        super().setUp()
        registry.reset()
        self.addCleanup(registry.reset)
        loaded = [
            registry.Loaded(Watcher(), "apx-watcher", "0.1.0"),
            registry.Loaded(Stranger(), "apx-stranger", "0.1.0"),
        ]
        patcher = mock.patch.object(
            registry.Plugins, "find", staticmethod(lambda known=None: loaded)
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        Watcher.seen = []
        Stranger.seen = []

    def sentry_app(self):
        self.client.put(
            "/api/v1/oauth/apps/sentry",
            json={"client_id": "cid", "client_secret": "sec"},
            headers=self.h(),
        )

    def connect_sentry(self, grant):
        from app.services.integrations.connections import SentryProvider

        self.sentry_app()
        started = self.client.post(
            "/api/v1/oauth/sentry/start",
            json={"origin": "https://ap.example.com"},
            headers=self.h(),
        ).json()
        state = started["url"].split("state=")[1].split("&")[0]
        self.patch(SentryProvider, "exchange_code", lambda self, app, o, c: grant)

        return self.client.post(
            "/api/v1/oauth/sentry/callback",
            json={"origin": "https://ap.example.com", "state": state, "code": "c"},
            headers=self.h(),
        ).json()

    def test_start_asks_sentry_for_what_the_plugins_declare(self):
        self.sentry_app()
        started = self.client.post(
            "/api/v1/oauth/sentry/start",
            json={"origin": "https://ap.example.com"},
            headers=self.h(),
        ).json()

        self.assertTrue(
            started["url"].startswith(
                "https://sentry.io/oauth/authorize/?client_id=cid&redirect_uri=https%3A%2F%2Fap.example.com%2Fapi%2Foauth%2Fsentry%2Fcallback"
            )
        )
        self.assertIn("scope=org%3Aread+member%3Aadmin+team%3Awrite", started["url"])

    def test_github_asks_for_the_plugins_scopes_and_permissions(self):
        self.client.put(
            "/api/v1/oauth/apps/github",
            json={"client_id": "cid", "client_secret": "sec"},
            headers=self.h(),
        )
        started = self.client.post(
            "/api/v1/oauth/github/start",
            json={"origin": "https://ap.example.com"},
            headers=self.h(),
        ).json()
        self.client.delete("/api/v1/oauth/apps/github", headers=self.h())
        manifest = self.client.post(
            "/api/v1/oauth/github/manifest",
            json={"origin": "https://ap.example.com", "host": "ap.example.com"},
            headers=self.h(),
        ).json()

        self.assertIn(
            "scope=repo+workflow+read%3Aorg+delete_repo+admin%3Aorg+read%3Aproject",
            started["url"],
        )
        permissions = manifest["manifest"]["default_permissions"]
        self.assertEqual(
            (permissions["members"], permissions["organization_projects"]),
            ("write", "read"),
        )

    def test_a_connection_is_listed_and_handed_to_the_plugin_that_declares_it(self):
        from app.core.abc import TokenGrant

        rows = self.client.get("/api/v1/connections", headers=self.h()).json()
        self.assertEqual(
            [(r["kind"], r["configured"], r["connected"]) for r in rows],
            [("sentry", False, False)],
        )

        done = self.connect_sentry(
            TokenGrant(
                "tok-s", "ref-s", None, ("org:read", "member:admin"), "ana@example.com"
            )
        )
        self.assertEqual(done["query"], {"connected": "sentry"})

        row = self.client.get("/api/v1/connections", headers=self.h()).json()[0]
        self.assertEqual(
            (row["connected"], row["login"], row["scopes"], row["missing"]),
            (True, "ana@example.com", ["org:read", "member:admin"], ["team:write"]),
        )
        self.assertNotIn("tok-s", str(row))

        self.client.put(
            "/api/v1/plugins/watcher/options",
            json={"options": {"org": "acme"}},
            headers=self.h(),
        )
        audit = self.client.get("/api/v1/access/audit", headers=self.h()).json()

        self.assertEqual([s["service"] for s in audit["services"]], ["watcher"])
        sentry, github = Watcher.seen[-1]
        self.assertEqual(
            (sentry.token, sentry.scopes), ("tok-s", ("org:read", "member:admin"))
        )
        self.assertIsNone(github)
        self.assertEqual(set(Stranger.seen), {None})

    def test_an_expiring_token_is_refreshed_before_it_is_handed_over(self):
        from app.core.abc import TokenGrant
        from app.core.shared.clock import now
        from app.services.integrations.connections import SentryProvider

        self.connect_sentry(
            TokenGrant("old", "ref", now() + timedelta(seconds=5), ("org:read",), "ana")
        )
        self.patch(
            SentryProvider,
            "refresh",
            lambda self, app, token: TokenGrant(
                "new", "ref-2", now() + timedelta(days=30), None, ""
            ),
        )
        self.client.put(
            "/api/v1/plugins/watcher/options",
            json={"options": {"org": "acme"}},
            headers=self.h(),
        )
        self.client.get("/api/v1/access/audit", headers=self.h())
        self.client.get("/api/v1/access/audit", headers=self.h())

        self.assertEqual([s.token for s, _ in Watcher.seen[-2:]], ["new", "new"])
        self.assertEqual(Watcher.seen[-1][0].scopes, ("org:read",))

    def test_the_github_host_is_handed_to_a_plugin_that_declares_it(self):
        from app.core.abc import TokenGrant

        self.client.post(
            "/api/v1/hosts",
            json={"kind": "github", "token": "ghp-x", "username": "ana"},
            headers=self.h(),
        )
        self.connect_sentry(TokenGrant("s"))
        self.client.put(
            "/api/v1/plugins/watcher/options",
            json={"options": {"org": "acme"}},
            headers=self.h(),
        )
        self.client.get("/api/v1/access/audit", headers=self.h())

        github = Watcher.seen[-1][1]
        self.assertEqual(
            (github.token, github.login, github.app), ("ghp-x", "ana", None)
        )

    def test_no_connection_is_a_failed_service_and_disconnect_forgets_it(self):
        from app.core.abc import TokenGrant

        self.client.put(
            "/api/v1/plugins/watcher/options",
            json={"options": {"org": "acme"}},
            headers=self.h(),
        )
        audit = self.client.get("/api/v1/access/audit", headers=self.h()).json()
        self.assertEqual(audit["services"][0]["error"], "watcher: connect Sentry")

        self.connect_sentry(TokenGrant("tok"))
        self.assertEqual(
            self.client.delete(
                "/api/v1/connections/sentry", headers=self.h()
            ).status_code,
            204,
        )
        self.assertFalse(
            self.client.get("/api/v1/connections", headers=self.h()).json()[0][
                "connected"
            ]
        )
        self.assertEqual(
            self.client.delete(
                "/api/v1/connections/nope", headers=self.h()
            ).status_code,
            404,
        )

    def test_a_plugin_asking_what_the_platform_asks_is_named_once(self):
        from app.core.abc import AccessReport, Owner
        from app.services.integrations.hosts import GithubProvider

        report = AccessReport(kind="github", login="ana")
        report.installations.append(
            Owner(
                "acme",
                "org",
                "all",
                "write",
                "write",
                "write",
                permissions={"members": "read", "administration": "write"},
            )
        )
        GithubProvider._check(report, "ana")

        self.assertEqual(
            [p for p in report.problems if "embers" in p],
            [
                'acme: organization permission "Members" is read; it must be "Read and write" to manage the organization\'s members and teams under Access. Change it in the app\'s Permissions & events, then accept the new permissions on the installation.'
            ],
        )
