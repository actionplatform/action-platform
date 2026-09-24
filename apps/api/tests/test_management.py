"""`/api/v1` management: projects and apps, teams, members and invitations, hosts, OAuth apps and flows, settings, template sources."""

from __future__ import annotations

from tests.test_access import GateCase


class ProjectsAndAppsTest(GateCase):
    def test_add_app_to_project_then_remove_project(self):
        from app.repositories.workspace.source import get_registry

        project = self.client.post(
            "/api/v1/projects", json={"name": "Web"}, headers=self.h()
        ).json()
        added = self.client.post(
            f"/api/v1/projects/{project['id']}/apps",
            json={"url": self.url},
            headers=self.h(),
        )
        self.assertEqual(added.status_code, 201, added.text)
        registry_id = added.json()["registry_id"]
        self.assertEqual(get_registry().get(registry_id).url, self.url)
        rows = self.client.get("/api/v1/projects", headers=self.h()).json()
        self.assertEqual(rows[0]["apps"][0]["registry_id"], registry_id)
        imports = self.client.get(
            f"/api/v1/projects/{project['id']}/apps/{added.json()['id']}/imports",
            headers=self.h(),
        ).json()
        self.assertEqual(imports, {"releases": [], "pull_requests": [], "errors": {}})
        removed = self.client.delete(
            f"/api/v1/projects/{project['id']}", headers=self.h()
        )
        self.assertEqual(removed.json()["removed"], [registry_id])
        self.assertEqual(
            self.client.get("/api/v1/projects", headers=self.h()).json(), []
        )
        self.assertEqual(
            self.client.get(
                "/api/apps", headers={"authorization": "Bearer shared"}
            ).json(),
            [],
        )

    def test_adding_a_github_url_without_a_host_is_refused(self):
        project = self.client.post(
            "/api/v1/projects", json={"name": "Web"}, headers=self.h()
        ).json()
        res = self.client.post(
            f"/api/v1/projects/{project['id']}/apps",
            json={"url": "https://github.com/acme/x.git"},
            headers=self.h(),
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("github", res.json()["detail"])

    def test_delete_app_and_host_assignment(self):
        from app.core.auth.crypto import Sealer
        from app.core.db.models import SourceHost

        project = self.client.post(
            "/api/v1/projects", json={"name": "Web"}, headers=self.h()
        ).json()
        app = self.client.post(
            f"/api/v1/projects/{project['id']}/apps",
            json={"url": self.url},
            headers=self.h(),
        ).json()
        with self.app.state.db.session() as s:
            s.add(
                SourceHost(
                    id="h1",
                    organization_id=self.org["id"],
                    kind="github",
                    name="GitHub",
                    token_encrypted=Sealer(self.app.state.secrets).seal("t"),
                )
            )
        res = self.client.put(
            f"/api/v1/projects/{project['id']}/apps/{app['id']}/host",
            json={"source_host_id": "h1"},
            headers=self.h(),
        )
        self.assertEqual(res.json()["source_host_id"], "h1")
        self.assertEqual(
            self.client.put(
                f"/api/v1/projects/{project['id']}/apps/{app['id']}/host",
                json={"source_host_id": "nope"},
                headers=self.h(),
            ).status_code,
            404,
        )
        removed = self.client.delete(
            f"/api/v1/projects/{project['id']}/apps/{app['id']}", headers=self.h()
        )
        self.assertEqual(removed.status_code, 200, removed.text)
        self.assertEqual(removed.json()["repositories"], [])
        self.assertEqual(
            self.client.get("/api/v1/projects", headers=self.h()).json()[0]["apps"], []
        )

    def _app_on_github(self):
        from app.core.auth.crypto import Sealer
        from app.core.db.models import SourceHost
        from app.services.projects.apps import AppService

        from action_platform.providers.source.github import SourceGithub

        project = self.client.post(
            "/api/v1/projects", json={"name": "Web"}, headers=self.h()
        ).json()
        app = self.client.post(
            f"/api/v1/projects/{project['id']}/apps",
            json={"url": self.url},
            headers=self.h(),
        ).json()

        with self.app.state.db.session() as s:
            s.add(
                SourceHost(
                    id="h1",
                    organization_id=self.org["id"],
                    kind="github",
                    name="GitHub",
                    token_encrypted=Sealer(self.app.state.secrets).seal("t"),
                )
            )

        deleted = []
        self.patch(AppService, "repository_of", lambda self, id: ("github", "acme/x"))
        self.patch(
            SourceGithub,
            "delete_repository",
            lambda self, repo: deleted.append((self.token, repo)),
        )

        return project, app, deleted

    def test_deleting_the_repository_needs_an_attached_host(self):
        project, app, deleted = self._app_on_github()

        refused = self.client.delete(
            f"/api/v1/projects/{project['id']}/apps/{app['id']}?repository=true",
            headers=self.h(),
        )

        self.assertEqual(refused.status_code, 409, refused.text)
        self.assertIn("no connected host", refused.json()["detail"])
        self.assertEqual(deleted, [])
        self.assertEqual(
            len(
                self.client.get("/api/v1/projects", headers=self.h()).json()[0]["apps"]
            ),
            1,
        )

    def test_deleting_the_repository_with_the_app_and_with_the_project(self):
        project, app, deleted = self._app_on_github()
        self.client.put(
            f"/api/v1/projects/{project['id']}/apps/{app['id']}/host",
            json={"source_host_id": "h1"},
            headers=self.h(),
        )

        kept = self.client.delete(
            f"/api/v1/projects/{project['id']}/apps/{app['id']}", headers=self.h()
        )
        self.assertEqual(kept.json()["repositories"], [])
        self.assertEqual(deleted, [])

        app = self.client.post(
            f"/api/v1/projects/{project['id']}/apps",
            json={"url": self.url},
            headers=self.h(),
        ).json()
        self.client.put(
            f"/api/v1/projects/{project['id']}/apps/{app['id']}/host",
            json={"source_host_id": "h1"},
            headers=self.h(),
        )

        removed = self.client.delete(
            f"/api/v1/projects/{project['id']}?repositories=true", headers=self.h()
        )

        self.assertEqual(removed.status_code, 200, removed.text)
        self.assertEqual(removed.json()["repositories"], ["acme/x"])
        self.assertEqual(deleted, [("t", "acme/x")])
        self.assertEqual(
            self.client.get("/api/v1/projects", headers=self.h()).json(), []
        )

    def test_viewer_cannot_manage(self):
        from app.core.db.models import Member

        with self.app.state.db.session() as s:
            s.query(Member).update({"role": "viewer"})
        res = self.client.post(
            "/api/v1/projects", json={"name": "Web"}, headers=self.h()
        )
        self.assertEqual(res.status_code, 403)


class TeamsAndMembersTest(GateCase):
    def test_team_lifecycle(self):
        team = self.client.post(
            "/api/v1/teams", json={"name": "Core"}, headers=self.h()
        ).json()
        self.assertEqual(
            self.client.put(
                f"/api/v1/teams/{team['id']}", json={"name": "Core 2"}, headers=self.h()
            ).json()["slug"],
            "core-2",
        )
        self.client.post(
            "/api/v1/teams/members",
            json={"team_id": team["id"], "user_id": self.user_id},
            headers=self.h(),
        )
        self.assertEqual(
            self.client.delete(
                f"/api/v1/teams/{team['id']}/members/{self.user_id}", headers=self.h()
            ).status_code,
            204,
        )
        self.assertEqual(
            self.client.get("/api/v1/teams", headers=self.h()).json()[0]["members"], []
        )
        self.assertEqual(
            self.client.delete(
                f"/api/v1/teams/{team['id']}", headers=self.h()
            ).status_code,
            204,
        )
        self.assertEqual(self.client.get("/api/v1/teams", headers=self.h()).json(), [])

    def test_invite_open_accept_and_last_owner_rule(self):
        invited = self.client.post(
            "/api/v1/invitations",
            json={"email": "Bob@example.com", "role": "developer"},
            headers=self.h(),
        )
        self.assertEqual(invited.status_code, 201, invited.text)
        open_view = self.client.get(f"/api/auth/invitations/{invited.json()['id']}")
        self.assertEqual(
            (
                open_view.status_code,
                open_view.json()["organization"]["slug"],
                open_view.json()["expired"],
            ),
            (200, "acme", False),
        )
        self.assertEqual(
            len(self.client.get("/api/v1/invitations", headers=self.h()).json()), 1
        )
        bob = self.client.post(
            "/api/auth/sign-up",
            json={
                "name": "Bob",
                "email": "bob@example.com",
                "password": "password1",
                "invitation_id": invited.json()["id"],
            },
        ).json()
        accepted = self.client.post(
            f"/api/auth/invitations/{invited.json()['id']}/accept",
            headers={"X-Session-Token": bob["session"]["token"]},
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)
        members = self.client.get("/api/v1/members", headers=self.h()).json()
        self.assertEqual(
            {m["email"]: m["role"] for m in members},
            {"ana@example.com": "owner", "bob@example.com": "developer"},
        )
        self.assertEqual(
            self.client.delete(
                f"/api/v1/members/{self.user_id}", headers=self.h()
            ).status_code,
            400,
        )
        promoted = self.client.post(
            "/api/v1/members/role",
            json={"user_id": bob["user"]["id"], "role": "admin"},
            headers=self.h(),
        )
        self.assertEqual(promoted.status_code, 200, promoted.text)
        bob_h = {"Authorization": f"Bearer {bob['session']['token']}"}
        self_promotion = self.client.post(
            "/api/v1/members/role",
            json={"user_id": bob["user"]["id"], "role": "owner"},
            headers=bob_h,
        )
        self.assertEqual(self_promotion.status_code, 403, self_promotion.text)
        demote_owner = self.client.post(
            "/api/v1/members/role",
            json={"user_id": self.user_id, "role": "viewer"},
            headers=bob_h,
        )
        self.assertEqual(demote_owner.status_code, 403)
        remove_owner = self.client.delete(
            f"/api/v1/members/{self.user_id}", headers=bob_h
        )
        self.assertEqual(remove_owner.status_code, 403)
        self.assertEqual(
            self.client.delete(
                f"/api/v1/members/{bob['user']['id']}", headers=self.h()
            ).status_code,
            204,
        )
        self.assertEqual(
            self.client.get("/api/v1/invitations", headers=self.h()).json(), []
        )


class HostsAndSettingsTest(GateCase):
    def test_token_host_lifecycle(self):
        added = self.client.post(
            "/api/v1/hosts",
            json={"kind": "github", "token": "ghp_1", "default_owner": "acme"},
            headers=self.h(),
        )
        self.assertEqual(added.status_code, 201, added.text)
        host = added.json()
        self.assertEqual((host["name"], host["auth_kind"]), ("GitHub", "token"))
        self.assertEqual(
            self.client.put(
                f"/api/v1/hosts/{host['id']}/token",
                json={"token": "ghp_2"},
                headers=self.h(),
            ).status_code,
            204,
        )
        self.assertEqual(
            self.client.put(
                f"/api/v1/hosts/{host['id']}/owner",
                json={"owner": "other"},
                headers=self.h(),
            ).status_code,
            204,
        )
        listed = self.client.get("/api/v1/hosts", headers=self.h()).json()
        self.assertEqual(listed[0]["default_owner"], "other")
        self.assertNotIn("token", listed[0])
        from app.services.integrations.hosts.directory import IntegrationsDirectory

        with self.app.state.db.session() as s:
            self.assertEqual(
                IntegrationsDirectory(s, self.app.state.sealer)
                .credentials_for(self.org["id"], host["id"])
                .token,
                "ghp_2",
            )
        self.assertEqual(
            self.client.delete(
                f"/api/v1/hosts/{host['id']}", headers=self.h()
            ).status_code,
            204,
        )
        self.assertEqual(self.client.get("/api/v1/hosts", headers=self.h()).json(), [])

    def test_git_author_and_template_sources(self):
        self.assertEqual(
            self.client.get("/api/v1/settings/git-author", headers=self.h()).json()[
                "name"
            ],
            "Action Platform",
        )
        saved = self.client.put(
            "/api/v1/settings/git-author",
            json={"name": "Bot", "email": "Bot@acme.io"},
            headers=self.h(),
        ).json()
        self.assertEqual(saved, {"name": "Bot", "email": "bot@acme.io"})
        self.assertEqual(
            self.client.put(
                "/api/v1/settings/git-author",
                json={"name": "", "email": "x"},
                headers=self.h(),
            ).status_code,
            400,
        )
        added = self.client.post(
            "/api/v1/template-sources",
            json={"name": "Mine", "url": "https://example.com/t.git", "ref": ""},
            headers=self.h(),
        )
        self.assertEqual(
            (added.status_code, added.json()["name"], added.json()["ref"]),
            (201, "mine", "main"),
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/template-sources",
                json={"name": "official", "url": "https://x/y.git"},
                headers=self.h(),
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.delete(
                f"/api/v1/template-sources/{added.json()['id']}", headers=self.h()
            ).status_code,
            204,
        )
        self.assertEqual(
            self.client.get("/api/v1/template-sources", headers=self.h()).json(), []
        )

    def test_oauth_apps_and_start(self):
        rows = self.client.get("/api/v1/oauth/apps", headers=self.h()).json()
        self.assertEqual([r["configured"] for r in rows], [False, False, False])
        self.assertEqual(
            self.client.post(
                "/api/v1/oauth/github/start",
                json={"origin": "https://ap.example.com"},
                headers=self.h(),
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.put(
                "/api/v1/oauth/apps/github",
                json={"client_id": "cid", "client_secret": "sec"},
                headers=self.h(),
            ).status_code,
            204,
        )
        rows = self.client.get("/api/v1/oauth/apps", headers=self.h()).json()
        self.assertEqual((rows[0]["configured"], rows[0]["client_id"]), (True, "cid"))
        started = self.client.post(
            "/api/v1/oauth/github/start",
            json={"origin": "https://ap.example.com", "return_to": "/settings"},
            headers=self.h(),
        ).json()
        self.assertTrue(
            started["url"].startswith(
                "https://github.com/login/oauth/authorize?client_id=cid&redirect_uri=https%3A%2F%2Fap.example.com%2Fapi%2Foauth%2Fgithub%2Fcallback&state="
            )
        )
        state = started["url"].split("state=")[1].split("&")[0]
        denied = self.client.post(
            "/api/v1/oauth/github/callback",
            json={
                "origin": "https://ap.example.com",
                "state": state,
                "error": "access_denied",
            },
            headers=self.h(),
        ).json()
        self.assertEqual(
            denied,
            {"return_to": "/settings", "query": {"oauth_error": "access_denied"}},
        )
        bad = self.client.post(
            "/api/v1/oauth/github/callback",
            json={"origin": "https://ap.example.com", "state": "x.y", "code": "c"},
            headers=self.h(),
        )
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(
            self.client.post(
                "/api/v1/oauth/github/manifest",
                json={"origin": "https://ap.example.com", "host": "ap.example.com"},
                headers=self.h(),
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.delete(
                "/api/v1/oauth/apps/github", headers=self.h()
            ).status_code,
            204,
        )
        manifest = self.client.post(
            "/api/v1/oauth/github/manifest",
            json={
                "origin": "https://ap.example.com",
                "host": "ap.example.com",
                "github_org": "acme",
            },
            headers=self.h(),
        ).json()
        self.assertTrue(
            manifest["target"].startswith(
                "https://github.com/organizations/acme/settings/apps/new?state="
            )
        )
        self.assertEqual(
            manifest["manifest"]["callback_urls"],
            ["https://ap.example.com/api/oauth/github/callback"],
        )

    def test_oauth_callback_connects_a_host(self):
        from app.services.integrations.hosts import GitlabProvider

        self.client.put(
            "/api/v1/oauth/apps/gitlab",
            json={"client_id": "cid", "client_secret": "sec"},
            headers=self.h(),
        )
        started = self.client.post(
            "/api/v1/oauth/gitlab/start",
            json={"origin": "https://ap.example.com"},
            headers=self.h(),
        ).json()
        state = started["url"].split("state=")[1].split("&")[0]
        self.patch(
            GitlabProvider,
            "exchange_code",
            lambda self, app, origin, code: ("access", "refresh", None),
        )
        self.patch(GitlabProvider, "identity", lambda self, app, token: ("ana", "Ana"))
        done = self.client.post(
            "/api/v1/oauth/gitlab/callback",
            json={"origin": "https://ap.example.com", "state": state, "code": "c"},
            headers=self.h(),
        ).json()
        self.assertEqual(done["query"], {"connected": "gitlab"})
        hosts = self.client.get("/api/v1/hosts", headers=self.h()).json()
        self.assertEqual(
            (
                hosts[0]["kind"],
                hosts[0]["auth_kind"],
                hosts[0]["login"],
                hosts[0]["name"],
            ),
            ("gitlab", "oauth", "ana", "GitLab · ana"),
        )
        self.assertEqual(
            self.client.delete(
                "/api/v1/oauth/gitlab/hosts/ana", headers=self.h()
            ).status_code,
            204,
        )
        self.assertEqual(self.client.get("/api/v1/hosts", headers=self.h()).json(), [])

    def test_oauth_callback_stores_the_providers_token_username(self):
        from app.services.integrations.hosts import BitbucketProvider

        self.client.put(
            "/api/v1/oauth/apps/bitbucket",
            json={"client_id": "cid", "client_secret": "sec"},
            headers=self.h(),
        )
        started = self.client.post(
            "/api/v1/oauth/bitbucket/start",
            json={"origin": "https://ap.example.com"},
            headers=self.h(),
        ).json()
        state = started["url"].split("state=")[1].split("&")[0]
        self.patch(
            BitbucketProvider,
            "exchange_code",
            lambda self, app, origin, code: ("access", None, None),
        )
        self.patch(
            BitbucketProvider, "identity", lambda self, app, token: ("ana", "Ana")
        )
        self.patch(BitbucketProvider, "owner", lambda self, token, installation: "team")
        done = self.client.post(
            "/api/v1/oauth/bitbucket/callback",
            json={"origin": "https://ap.example.com", "state": state, "code": "c"},
            headers=self.h(),
        ).json()
        self.assertEqual(done["query"], {"connected": "bitbucket"})
        hosts = self.client.get("/api/v1/hosts", headers=self.h()).json()
        self.assertEqual(
            (hosts[0]["username"], hosts[0]["default_owner"]),
            ("x-token-auth", "team"),
        )


class DeadTokenTest(GateCase):
    def test_expired_oauth_host_without_refresh_answers_not_ok(self):
        from datetime import timedelta

        from app.core.auth.crypto import Sealer
        from app.core.db.models import SourceHost
        from app.core.shared.clock import now

        sealer = Sealer(self.app.state.secrets)

        with self.app.state.db.session() as s:
            s.add(
                SourceHost(
                    id="h1",
                    organization_id=self.org["id"],
                    kind="gitlab",
                    name="GitLab · ana",
                    token_encrypted=sealer.seal("old"),
                    refresh_token_encrypted=sealer.seal("dead"),
                    expires_at=now() - timedelta(hours=1),
                    auth_kind="oauth",
                    login="ana",
                )
            )

        res = self.client.get("/api/v1/hosts/h1/access", headers=self.h())
        self.assertEqual(res.status_code, 200, res.text)
        self.assertFalse(res.json()["ok"])
        self.assertIn("reconnect the host", res.json()["error"])


class InjectedProvidersTest(GateCase):
    def override(self, providers):
        from app.api.dependencies import get_host_providers

        self.app.dependency_overrides[get_host_providers] = lambda: providers
        self.addCleanup(self.app.dependency_overrides.clear)

    def test_routes_use_the_injected_providers(self):
        from app.services.integrations.hosts import HostProviders

        self.override(HostProviders())
        res = self.client.post(
            "/api/v1/oauth/gitlab/start",
            json={"origin": "https://ap.example.com"},
            headers=self.h(),
        )
        self.assertEqual(res.status_code, 404, res.text)

    def test_refresh_and_access_go_through_the_injected_provider(self):
        from datetime import timedelta

        from app.core.abc import AccessReport
        from app.core.auth.crypto import Sealer
        from app.core.db.models import SourceHost
        from app.core.shared.clock import now
        from app.services.integrations.hosts import GitlabProvider, HostProviders

        seen = []

        class FakeGitlab(GitlabProvider):
            def refresh(self, app, refresh_token):
                seen.append(refresh_token)
                return "fresh", None, None

            def access(self, creds, app_slug):
                seen.append(creds.token)
                return AccessReport(kind=self.kind, login="ana")

        self.override(HostProviders(FakeGitlab()))
        self.client.put(
            "/api/v1/oauth/apps/gitlab",
            json={"client_id": "cid", "client_secret": "sec"},
            headers=self.h(),
        )
        sealer = Sealer(self.app.state.secrets)

        with self.app.state.db.session() as s:
            s.add(
                SourceHost(
                    id="h1",
                    organization_id=self.org["id"],
                    kind="gitlab",
                    name="GitLab · ana",
                    token_encrypted=sealer.seal("old"),
                    refresh_token_encrypted=sealer.seal("r1"),
                    expires_at=now() - timedelta(hours=1),
                    auth_kind="oauth",
                    login="ana",
                )
            )

        res = self.client.get("/api/v1/hosts/h1/access", headers=self.h())
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["login"], "ana")
        self.assertEqual(seen, ["r1", "fresh"])
