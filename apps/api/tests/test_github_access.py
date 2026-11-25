from __future__ import annotations

from unittest import mock

from action_platform.abc import Plugin
from action_platform.core.service_access import AccessError
from action_platform.plugins import registry
from action_platform.testing.access import MemoryProvider
from action_platform.testing.github import FakeGitHub
from tests.test_access import GateCase


class OldGitHub(Plugin):
    slug = "github"
    fails = False
    service = MemoryProvider("github")

    def access(self, options):
        if OldGitHub.fails:
            raise AccessError("github: the token lacks the read:org, repo scope")

        return OldGitHub.service


class GitHubAccessTest(GateCase):
    def setUp(self):
        super().setUp()
        registry.reset()
        self.addCleanup(registry.reset)
        self.plugins: list = []
        patcher = mock.patch.object(
            registry.Plugins, "find", staticmethod(lambda known=None: self.plugins)
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.github = FakeGitHub()
        self.github.members = {"ana": "admin", "bot": "admin"}
        self.github.repo("api")
        self.reached: list = []
        patcher = mock.patch(
            "app.services.service_access.github.client", self.client_for
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def client_for(self, token, url):
        self.reached.append((token, url))

        return self.github

    def connect(self, owner="acme", **extra):
        answer = self.client.post(
            "/api/v1/hosts",
            json={
                "kind": "github",
                "token": "ghp-x",
                "username": "ana",
                "default_owner": owner,
                **extra,
            },
            headers=self.h(),
        )
        self.assertEqual(answer.status_code, 201, answer.text)

    def audit(self):
        return self.client.get("/api/v1/access/audit", headers=self.h())

    def test_without_a_github_connection_there_is_nothing_to_manage(self):
        answer = self.audit()

        self.assertEqual(answer.status_code, 400)
        self.assertIn("connect GitHub under Settings → Git", answer.json()["detail"])

    def test_the_github_connection_brings_the_github_service(self):
        self.connect()

        row = self.audit().json()["services"][0]

        self.assertEqual((row["service"], row["ok"], row["live"]), ("github", True, 2))
        self.assertEqual(row["levels"]["repo"][0], "pull")
        self.assertEqual(self.reached, [("ghp-x", "https://api.github.com")])
        self.assertIn(("GET", "orgs/acme/members", None), self.github.calls)

    def test_a_connection_without_an_owner_is_a_failed_service(self):
        self.connect(owner="")

        row = self.audit().json()["services"][0]

        self.assertEqual((row["service"], row["ok"]), ("github", False))
        self.assertIn("owner of the GitHub connection", row["error"])
        self.assertEqual(self.reached, [])

    def test_the_first_sync_imports_and_changes_nothing(self):
        self.connect()

        plan = self.client.post(
            "/api/v1/access/sync",
            json={"apply": True, "links": {"ana@example.com": {"github": "ana"}}},
            headers=self.h(),
        ).json()

        self.assertEqual((plan["imported"], plan["changes"]), (["github"], []))
        self.assertEqual(self.github.writes(), [])

    def test_another_organizations_github_connection_is_never_used(self):
        from app.core.db.models import Organization
        from app.repositories.integrations import HostsWrites

        with self.app.state.db.session() as s:
            s.add(Organization(id="org-b", name="Beta", slug="beta"))
            s.flush()
            HostsWrites(s, self.app.state.sealer).add_host(
                "org-b", "github", "", "ghp-b", default_owner="beta"
            )
            s.commit()

        self.assertEqual(self.audit().status_code, 400)
        self.assertEqual(self.reached, [])

    def test_an_installed_github_plugin_never_replaces_the_built_in(self):
        self.plugins.append(registry.Loaded(OldGitHub(), "apx-github", "0.2.1"))
        OldGitHub.service = MemoryProvider("github")
        OldGitHub.service.add("stranger", "org", "admin")
        self.connect()

        services = self.audit().json()["services"]

        self.assertEqual(
            [(s["service"], s["ok"], s["live"]) for s in services],
            [("github", True, 2)],
        )
        self.assertEqual(services[0]["outside_accounts"], ["ana", "bot"])

        OldGitHub.fails = True
        self.addCleanup(setattr, OldGitHub, "fails", False)

        services = self.audit().json()["services"]

        self.assertEqual(
            [(s["service"], s["ok"], s["error"]) for s in services],
            [("github", True, None)],
        )

    def test_the_checks_read_the_organization_through_the_connection(self):
        self.connect()

        settings = self.client.get(
            "/api/v1/access/github/repo-settings?repo=api", headers=self.h()
        ).json()
        protection = self.client.get(
            "/api/v1/access/github/branch-protection", headers=self.h()
        ).json()

        self.assertEqual(settings["org"], "acme")
        self.assertEqual(
            [(r["repo"], r["visibility"]) for r in settings["repos"]],
            [("api", "public")],
        )
        self.assertEqual(
            [(r["repo"], r["protected"]) for r in protection["repos"]],
            [("api", False)],
        )
        self.assertEqual(self.github.writes(), [])

    def test_the_checks_without_a_connection_say_to_connect(self):
        answer = self.client.get(
            "/api/v1/access/github/repo-settings", headers=self.h()
        )

        self.assertEqual(answer.status_code, 400)
        self.assertIn("connect GitHub under Settings → Git", answer.json()["detail"])

    def test_the_checks_need_org_manage(self):
        self.connect()
        token = self.token("read,write,release")

        for path in ("branch-protection", "repo-settings"):
            with self.subTest(path=path):
                answer = self.client.get(
                    f"/api/v1/access/github/{path}", headers=self.h(token)
                )

                self.assertEqual(answer.status_code, 403)

    def test_connecting_github_asks_for_what_access_needs(self):
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

        self.assertIn("admin%3Aorg", started["url"])
        permissions = manifest["manifest"]["default_permissions"]
        self.assertEqual(
            (permissions["members"], permissions["administration"]),
            ("write", "write"),
        )
