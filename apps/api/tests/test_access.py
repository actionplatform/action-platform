"""`/api/v1`: the gate in front of the API — who the caller is, what their role, scope and reach allow, what gets filled in."""

from __future__ import annotations

import unittest

from action_platform.settings import settings
from action_platform.testing.fixtures import TempCase, git, platform_repo

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient, "fastapi is not installed")
class GateCase(TempCase):
    def setUp(self):
        super().setUp()
        from app.api.routers.auth import LIMITS
        from app.api.app import build

        self.setenv("AP_HOME", str(self.tmp_path / "home"))
        self.patch(
            settings,
            "WORKSPACES",
            self.tmp_path / "home" / "action-platform" / "workspaces",
        )
        self.patch(settings, "WORKSPACE_TTL", 0)
        self.patch(settings, "ALLOW_UNAUTHENTICATED_API", False)
        self.patch(settings, "ALLOW_FILE_URLS", True)
        for limiter in LIMITS.values():
            limiter.hits.clear()
        self.app = build(
            token="shared",
            database_url=f"sqlite:///{self.tmp_path / 'gate.db'}",
            auth_secret="s3cret",
            public_url="https://ap.example.com",
        )
        self.client = TestClient(self.app)
        self.repo = platform_repo(self.tmp_path)
        git(self.repo, "checkout", "-q", "main")
        self.url = self.repo.as_uri()
        signed = self.client.post(
            "/api/auth/sign-up",
            json={"name": "Ana", "email": "ana@example.com", "password": "password1"},
        ).json()
        self.session = signed["session"]["token"]
        self.user_id = signed["user"]["id"]
        self.org = self.client.post(
            "/api/auth/organizations",
            json={"name": "Acme", "slug": "acme"},
            headers=self.h(),
        ).json()

    def h(self, token: str | None = None) -> dict:
        return {"Authorization": f"Bearer {token or self.session}"}

    def register(self) -> str:
        from app.core.db.models import App, Project

        res = self.client.post(
            "/api/apps",
            json={"url": self.url},
            headers={"authorization": "Bearer shared"},
        )
        assert res.status_code == 201, res.text
        registry_id = res.json()["id"]
        with self.app.state.db.session() as s:
            s.add(
                Project(id="p1", organization_id=self.org["id"], name="Web", slug="web")
            )
            s.add(App(id="a1", project_id="p1", registry_id=registry_id, name="demo"))
        return registry_id

    def token(self, scope: str) -> str:
        res = self.client.post(
            "/api/v1/tokens", json={"scope": scope, "name": "t"}, headers=self.h()
        )
        assert res.status_code == 200, res.text
        return res.json()["token"]


class IdentityTest(GateCase):
    def test_unauthenticated_and_shared_secret_do_not_pass(self):
        self.assertEqual(self.client.get("/api/v1/me").status_code, 401)
        self.assertEqual(
            self.client.get(
                "/api/v1/me", headers={"authorization": "Bearer shared"}
            ).status_code,
            401,
        )

    def test_me_by_session_cookie_and_by_token(self):
        me = self.client.get("/api/v1/me", headers=self.h()).json()
        self.assertEqual(
            (me["organization"]["slug"], me["role"], me["role_label"]),
            ("acme", "owner", "Owner"),
        )
        self.assertTrue(me["permissions"]["org.manage"])
        signed = self.client.get(
            "/api/auth/session", headers={"X-Session-Token": self.session}
        ).json()
        by_cookie = self.client.get(
            "/api/v1/me",
            headers={
                "cookie": f"better-auth.session_token={signed['session']['cookie']}"
            },
        )
        self.assertEqual(by_cookie.status_code, 200, by_cookie.text)
        raw = self.token("read write")
        via = self.client.get(
            "/api/v1/me",
            headers={**self.h(raw), "X-Action-Platform-Client": "Claude Code/1"},
        ).json()
        self.assertEqual(via["scope"], ["read", "write"])
        self.assertFalse(via["permissions"]["app.release"])
        tokens = self.client.get(
            "/api/auth/tokens", headers={"X-Session-Token": self.session}
        ).json()
        self.assertEqual(tokens[0]["clients"][0]["name"], "Claude Code/1")

    def test_organizations_and_directory(self):
        orgs = self.client.get("/api/v1/organizations", headers=self.h()).json()
        self.assertEqual(
            orgs[0]["grantable_scopes"], ["read", "write", "release", "admin"]
        )
        created = self.client.post(
            "/api/v1/projects", json={"name": "Web"}, headers=self.h()
        )
        self.assertEqual(created.status_code, 201, created.text)
        team = self.client.post(
            "/api/v1/teams", json={"name": "Core"}, headers=self.h()
        ).json()
        self.assertEqual(
            self.client.post(
                "/api/v1/teams/members",
                json={"team_id": team["id"], "user_id": self.user_id},
                headers=self.h(),
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/projects/team",
                json={"project_id": created.json()["id"], "team_id": team["id"]},
                headers=self.h(),
            ).status_code,
            200,
        )
        projects = self.client.get("/api/v1/projects", headers=self.h()).json()
        self.assertEqual(projects[0]["team"]["name"], "Core")
        teams = self.client.get("/api/v1/teams", headers=self.h()).json()
        self.assertEqual(teams[0]["members"][0]["email"], "ana@example.com")
        members = self.client.get("/api/v1/members", headers=self.h()).json()
        self.assertEqual(members[0]["role_label"], "Owner")
        last_owner = self.client.post(
            "/api/v1/members/role",
            json={"user_id": self.user_id, "role": "viewer"},
            headers=self.h(),
        )
        self.assertEqual(last_owner.status_code, 400)

    def test_management_needs_role_and_scope(self):
        raw = self.token("read write")
        refused = self.client.post(
            "/api/v1/projects", json={"name": "X"}, headers=self.h(raw)
        )
        self.assertEqual(refused.status_code, 403)
        self.assertIn("scope", refused.json()["detail"])


class AppsTest(GateCase):
    def test_apps_are_filtered_to_the_organization_and_reach(self):
        registry_id = self.register()
        listed = self.client.get("/api/v1/apps", headers=self.h()).json()
        self.assertEqual([a["id"] for a in listed], [registry_id])
        self.assertEqual(
            self.client.get(
                f"/api/v1/apps/{registry_id}", headers=self.h()
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/api/v1/apps/nope", headers=self.h()).status_code, 404
        )
        narrow = self.token(f"read org:{self.org['id']} project:p1 app:a1")
        self.assertEqual(
            len(self.client.get("/api/v1/apps", headers=self.h(narrow)).json()), 1
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/apps", json={"url": self.url}, headers=self.h(narrow)
            ).status_code,
            403,
        )

    def test_unexposed_and_forbidden_routes(self):
        registry_id = self.register()
        self.assertEqual(
            self.client.delete(
                f"/api/v1/apps/{registry_id}/nope", headers=self.h()
            ).status_code,
            404,
        )
        from app.core.db.models import Member

        with self.app.state.db.session() as s:
            s.query(Member).update({"role": "viewer"})
        self.client.get("/api/v1/me", headers=self.h())
        refused = self.client.post(
            f"/api/v1/apps/{registry_id}/sync", json={}, headers=self.h()
        )
        self.assertEqual(refused.status_code, 403)
        self.assertIn("viewer", refused.json()["detail"])

    def test_credentials_and_identity_are_filled_in(self):
        from app.core.db.models import OrganizationSetting

        registry_id = self.register()
        with self.app.state.db.session() as s:
            s.add(
                OrganizationSetting(
                    organization_id=self.org["id"],
                    git_author_name="Bot",
                    git_author_email="bot@acme.io",
                )
            )
        from app.services.apps import AppService

        seen = {}
        original = AppService.sync

        def spy(service, id, credentials=None, reset=False):
            seen["credentials"] = credentials.model_dump() if credentials else None
            return original(service, id, credentials, reset=reset)

        self.patch(AppService, "sync", spy)
        res = self.client.post(
            f"/api/v1/apps/{registry_id}/sync", json={}, headers=self.h()
        )
        self.assertIn(res.status_code, (200, 400), res.text)
        self.assertEqual(
            (seen["credentials"]["author_name"], seen["credentials"]["author_email"]),
            ("Bot", "bot@acme.io"),
        )
        listed = self.client.get("/api/v1/projects", headers=self.h()).json()
        self.assertIsNotNone(listed[0]["apps"][0]["last_synced_at"])

    def test_source_host_token_is_decrypted_from_the_web_apps_ciphertext(self):
        from app.core.auth.crypto import Sealer
        from app.core.db.models import SourceHost
        from app.services.directory import DirectoryService

        sealer = Sealer(self.app.state.secrets)
        with self.app.state.db.session() as s:
            s.add(
                SourceHost(
                    id="h1",
                    organization_id=self.org["id"],
                    kind="github",
                    name="GitHub",
                    token_encrypted=sealer.seal("ghp_x"),
                    default_owner="acme",
                    auth_kind="token",
                )
            )
        with self.app.state.db.session() as s:
            creds = DirectoryService(s, sealer).credentials_for(self.org["id"], "h1")
        self.assertEqual(
            (creds.kind, creds.token, creds.owner), ("github", "ghp_x", "acme")
        )
        with self.app.state.db.session() as s:
            self.assertEqual(
                DirectoryService(s, sealer).host_id_for_url(
                    self.org["id"], "https://github.com/acme/x.git"
                ),
                "h1",
            )


class MatrixTest(GateCase):
    def test_matrix_carries_the_organizations_template_sources(self):
        from app.core.db.models import TemplateSource

        with self.app.state.db.session() as s:
            s.add(
                TemplateSource(
                    id="t1",
                    organization_id=self.org["id"],
                    name="mine",
                    url="https://example.com/x.git",
                    ref="v1",
                )
            )
        with self.app.state.db.session() as s:
            from app.services.directory import DirectoryService

            specs = DirectoryService(s).source_specs_of(self.org["id"])
        self.assertEqual(
            specs,
            [
                {
                    "name": "mine",
                    "url": "https://example.com/x.git",
                    "ref": "v1",
                    "credentials": None,
                }
            ],
        )
        with self.assertRaises(Exception):
            with self.app.state.db.session() as s:
                DirectoryService(s).source_spec_by_name(self.org["id"], "other")


class CatalogAndPreviewTest(GateCase):
    def test_access_catalog(self):
        rows = self.client.get("/api/v1/access", headers=self.h()).json()
        self.assertEqual(
            [r["id"] for r in rows["roles"]],
            ["owner", "admin", "deployer", "developer", "viewer"],
        )
        self.assertEqual(rows["roles"][3]["grantable_scopes"], ["read", "write"])
        self.assertEqual(rows["default_scopes"], ["read", "write", "release", "admin"])
        self.assertIn("app.release", [p["id"] for p in rows["permissions"]])

    def test_next_version_preview(self):
        registry_id = self.register()
        res = self.client.get(
            f"/api/v1/apps/{registry_id}/next-version",
            params={"level": "minor"},
            headers=self.h(),
        )
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(
            (body["current"], body["next"], body["prerelease"]),
            ("1.2.3", "1.3.0", False),
        )
        rc = self.client.get(
            f"/api/v1/apps/{registry_id}/next-version",
            params={"level": "patch", "branch": "feature/1"},
            headers=self.h(),
        ).json()
        self.assertEqual((rc["next"], rc["prerelease"]), ("1.2.4-rc.1", True))

    def test_branch_plan(self):
        registry_id = self.register()
        res = self.client.get(
            f"/api/v1/apps/{registry_id}/branches/plan",
            params={"kind": "feature", "code": "42", "slug": "Login Page"},
            headers=self.h(),
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(
            (res.json()["branch"], res.json()["base"]),
            ("feature/42-login-page", "main"),
        )
        hotfix = self.client.get(
            f"/api/v1/apps/{registry_id}/branches/plan",
            params={"kind": "hotfix", "code": "7"},
            headers=self.h(),
        ).json()
        self.assertEqual(hotfix["base"], "main")
