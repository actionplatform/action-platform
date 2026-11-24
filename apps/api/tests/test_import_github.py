"""Importing a GitHub organization: repositories → projects and apps, people → members and invitations, teams → teams."""

from __future__ import annotations

from tests.test_access import GateCase


class FakeGithub:
    kind = "github"

    def __init__(self, url: str) -> None:
        self.url = url

    def organizations(self):
        return [
            {"login": "ana", "name": "Ana", "kind": "user", "avatar": None},
            {"login": "acme", "name": "Acme Inc", "kind": "org", "avatar": None},
        ]

    def repositories(self, login):
        return [
            {
                "full_name": "acme/web",
                "name": "web",
                "description": "The web app",
                "private": True,
                "archived": False,
                "fork": False,
                "language": "Python",
                "default_branch": "main",
                "url": self.url,
                "pushed_at": None,
            },
            {
                "full_name": "acme/broken",
                "name": "broken",
                "description": None,
                "private": False,
                "archived": True,
                "fork": False,
                "language": None,
                "default_branch": "main",
                "url": "file:///nowhere/broken.git",
                "pushed_at": None,
            },
        ]

    def projects(self, login):
        return [
            {
                "number": 3,
                "title": "Storefront",
                "description": "Everything the customer sees",
                "closed": False,
                "url": "https://github.com/orgs/acme/projects/3",
                "repositories": ["acme/web", "acme/broken"],
            }
        ]

    def teams(self, login):
        return [
            {
                "slug": "platform",
                "name": "Platform",
                "description": "Owns the web",
                "members": ["ana", "bob", "ghost"],
                "repositories": ["acme/web"],
            }
        ]

    def people(self, login):
        return [
            {
                "login": "ana",
                "name": "Ana",
                "email": "ana@example.com",
                "avatar": None,
                "role": "org_admin",
            },
            {
                "login": "bob",
                "name": "Bob",
                "email": "bob@example.com",
                "avatar": None,
                "role": "team_maintainer",
            },
            {
                "login": "ghost",
                "name": "Ghost",
                "email": None,
                "avatar": None,
                "role": "member",
            },
        ]


class ImportCase(GateCase):
    def setUp(self):
        super().setUp()
        from app.core.auth.crypto import Sealer
        from app.core.db.models import SourceHost
        from app.services.projects.organization_import import client, context

        with self.app.state.db.session() as s:
            s.add(
                SourceHost(
                    id="gh",
                    organization_id=self.org["id"],
                    kind="github",
                    name="GitHub",
                    token_encrypted=Sealer(self.app.state.secrets).seal("t"),
                )
            )

        fake = FakeGithub(self.url)
        self.patch(client, "GithubDirectory", lambda creds: fake)
        url = self.url

        class KnownUrl:
            def __init__(self, value):
                self.value = value

            @property
            def repo(self):
                return "acme/web" if self.value == url else None

        self.patch(context, "GitUrl", KnownUrl)


class GithubImportTest(ImportCase):
    def test_lists_organizations_and_previews_one(self):
        orgs = self.client.get(
            "/api/v1/import/github/organizations?host=gh", headers=self.h()
        )
        self.assertEqual(orgs.status_code, 200, orgs.text)
        self.assertEqual(
            [o["login"] for o in orgs.json()["organizations"]], ["ana", "acme"]
        )

        preview = self.client.get(
            "/api/v1/import/github/organizations/acme?host=gh", headers=self.h()
        ).json()
        self.assertEqual(
            [(r["full_name"], r["imported_as"]) for r in preview["repositories"]],
            [("acme/web", None), ("acme/broken", None)],
        )
        self.assertEqual(preview["teams"][0]["exists"], False)
        self.assertEqual(
            (preview["projects"][0]["title"], preview["projects"][0]["exists"]),
            ("Storefront", False),
        )
        self.assertEqual(
            {p["login"]: p["status"] for p in preview["people"]},
            {"ana": "member", "bob": "invitable", "ghost": "no_email"},
        )

    def test_needs_a_github_host_and_org_manage(self):
        from app.core.db.models import Member

        missing = self.client.get(
            "/api/v1/import/github/organizations?host=nope", headers=self.h()
        )
        self.assertEqual(missing.status_code, 404)

        with self.app.state.db.session() as s:
            s.query(Member).update({"role": "developer"})

        forbidden = self.client.get(
            "/api/v1/import/github/organizations?host=gh", headers=self.h()
        )
        self.assertEqual(forbidden.status_code, 403)

    def test_import_runs_as_a_job(self):
        from app.services.jobs.worker import Worker

        queued = self.client.post(
            "/api/v1/import/github",
            json={
                "host_id": "gh",
                "organization": "acme",
                "repositories": ["acme/web", "acme/broken", "acme/missing", "lost"],
                "teams": ["platform"],
                "people": ["ana", "bob", "ghost"],
                "role": "developer",
            },
            headers=self.h(),
        )
        self.assertEqual(queued.status_code, 202, queued.text)
        job_id = queued.json()["job"]

        worker = Worker(self.app.state.db, self.app.state.secrets, "test")
        self.assertEqual(worker.run(once=True), 1)

        done = self.client.get(f"/api/v1/jobs/{job_id}", headers=self.h()).json()
        self.assertEqual(done["status"], "done", done)
        summary = done["result"]
        self.assertEqual(summary["projects"], ["web"])
        self.assertEqual(summary["teams"], ["Platform"])
        self.assertEqual(summary["members"], [])
        self.assertEqual(summary["invitations"], ["bob@example.com"])
        self.assertTrue(any(s.startswith("acme/broken:") for s in summary["skipped"]))
        self.assertIn("acme/missing: not found on the host", summary["skipped"])
        self.assertIn(
            "lost: not found on the host — name it as owner/name", summary["skipped"]
        )
        self.assertTrue(any(s.startswith("ghost:") for s in summary["skipped"]))

        projects = self.client.get("/api/v1/projects", headers=self.h()).json()
        self.assertEqual([p["name"] for p in projects], ["web"])
        self.assertEqual(len(projects[0]["apps"]), 1)
        teams = self.client.get("/api/v1/teams", headers=self.h()).json()
        self.assertEqual(teams[0]["name"], "Platform")
        self.assertEqual(projects[0]["team"]["id"], teams[0]["id"])
        self.assertEqual([m["email"] for m in teams[0]["members"]], ["ana@example.com"])

        again = self.client.get(
            "/api/v1/import/github/organizations/acme?host=gh", headers=self.h()
        ).json()
        self.assertEqual(summary["apps"], [])
        self.assertEqual(again["repositories"][0]["imported_as"], "web")
        self.assertTrue(again["teams"][0]["exists"])
        self.assertEqual(
            {p["login"]: p["status"] for p in again["people"]},
            {"ana": "member", "bob": "invited", "ghost": "no_email"},
        )

    def test_import_into_one_project(self):
        from app.services.jobs.worker import Worker

        project = self.client.post(
            "/api/v1/projects", json={"name": "Platform"}, headers=self.h()
        ).json()
        queued = self.client.post(
            "/api/v1/import/github",
            json={
                "host_id": "gh",
                "organization": "acme",
                "repositories": ["acme/web"],
                "teams": ["platform"],
                "project_id": project["id"],
            },
            headers=self.h(),
        )
        self.assertEqual(queued.status_code, 202, queued.text)
        Worker(self.app.state.db, self.app.state.secrets, "test").run(once=True)

        done = self.client.get(
            f"/api/v1/jobs/{queued.json()['job']}", headers=self.h()
        ).json()
        self.assertEqual(done["status"], "done", done)
        self.assertEqual(done["result"]["projects"], [])
        self.assertEqual(done["result"]["apps"], ["web → Platform"])

        projects = self.client.get("/api/v1/projects", headers=self.h()).json()
        self.assertEqual([p["name"] for p in projects], ["Platform"])
        self.assertEqual([a["name"] for a in projects[0]["apps"]], ["web"])
        self.assertEqual(projects[0]["team"]["name"], "Platform")

    def test_import_a_github_project_with_its_repositories(self):
        from app.services.jobs.worker import Worker

        queued = self.client.post(
            "/api/v1/import/github",
            json={"host_id": "gh", "organization": "acme", "projects": [{"number": 3}]},
            headers=self.h(),
        )
        self.assertEqual(queued.status_code, 202, queued.text)
        Worker(self.app.state.db, self.app.state.secrets, "test").run(once=True)

        done = self.client.get(
            f"/api/v1/jobs/{queued.json()['job']}", headers=self.h()
        ).json()
        self.assertEqual(done["status"], "done", done)
        self.assertEqual(done["result"]["projects"], ["Storefront"])
        self.assertEqual(done["result"]["apps"], ["web → Storefront"])
        self.assertTrue(
            any(s.startswith("acme/broken:") for s in done["result"]["skipped"])
        )

        projects = self.client.get("/api/v1/projects", headers=self.h()).json()
        self.assertEqual([p["name"] for p in projects], ["Storefront"])
        self.assertEqual([a["name"] for a in projects[0]["apps"]], ["web"])
        self.assertTrue(
            self.client.get(
                "/api/v1/import/github/organizations/acme?host=gh", headers=self.h()
            ).json()["projects"][0]["exists"]
        )

    def test_import_a_github_project_into_an_existing_project(self):
        from app.services.jobs.worker import Worker

        target = self.client.post(
            "/api/v1/projects", json={"name": "Shop"}, headers=self.h()
        ).json()
        queued = self.client.post(
            "/api/v1/import/github",
            json={
                "host_id": "gh",
                "organization": "acme",
                "projects": [{"number": 3, "project_id": target["id"]}],
            },
            headers=self.h(),
        )
        self.assertEqual(queued.status_code, 202, queued.text)
        Worker(self.app.state.db, self.app.state.secrets, "test").run(once=True)

        done = self.client.get(
            f"/api/v1/jobs/{queued.json()['job']}", headers=self.h()
        ).json()
        self.assertEqual(done["status"], "done", done)
        self.assertEqual(done["result"]["projects"], [])
        self.assertEqual(done["result"]["apps"], ["web → Shop"])

        projects = self.client.get("/api/v1/projects", headers=self.h()).json()
        self.assertEqual([p["name"] for p in projects], ["Shop"])
        self.assertEqual([a["name"] for a in projects[0]["apps"]], ["web"])


class LoginInvitationTest(ImportCase):
    def setUp(self):
        super().setUp()
        self.setenv("AP_GITHUB_CLIENT_ID", "cid")
        self.setenv("AP_GITHUB_CLIENT_SECRET", "csecret")

    def run_import(self, **body):
        from app.services.jobs.worker import Worker

        queued = self.client.post(
            "/api/v1/import/github",
            json={"host_id": "gh", "organization": "acme", **body},
            headers=self.h(),
        )
        self.assertEqual(queued.status_code, 202, queued.text)
        Worker(self.app.state.db, self.app.state.secrets, "test").run(once=True)
        done = self.client.get(
            f"/api/v1/jobs/{queued.json()['job']}", headers=self.h()
        ).json()
        self.assertEqual(done["status"], "done", done)

        return done["result"]

    def invitation(self, key: str) -> dict:
        rows = self.client.get("/api/v1/invitations", headers=self.h()).json()

        return next(r for r in rows if key in (r["email"], r["login"]))

    def sign_up(self, name: str, email: str, invitation: str) -> dict:
        res = self.client.post(
            "/api/auth/sign-up",
            json={
                "name": name,
                "email": email,
                "password": "password1",
                "invitation_id": invitation,
            },
        )
        self.assertEqual(res.status_code, 201, res.text)

        return {"X-Session-Token": res.json()["session"]["token"]}

    def prove(self, login: str) -> None:
        from app.services.integrations.hosts import github

        self.patch(
            github.GithubProvider,
            "exchange_code",
            lambda self, app, origin, code: ("tok", None, None),
        )
        self.patch(
            github.GithubProvider,
            "identity",
            lambda self, app, token: (login, login.title()),
        )

    def test_preview_offers_a_login_invitation_and_host_roles(self):
        preview = self.client.get(
            "/api/v1/import/github/organizations/acme?host=gh", headers=self.h()
        ).json()

        self.assertEqual(
            {p["login"]: (p["status"], p["role"]) for p in preview["people"]},
            {
                "ana": ("member", "org_admin"),
                "bob": ("invitable", "team_maintainer"),
                "ghost": ("invitable_login", "member"),
            },
        )

    def test_nobody_is_skipped_and_invitees_wait_for_their_teams(self):
        summary = self.run_import(
            teams=["platform"],
            people=["bob", "ghost"],
            roles={"org_admin": "admin", "team_maintainer": "deployer"},
        )

        self.assertEqual(summary["invitations"], ["bob@example.com"])
        self.assertEqual(summary["login_invitations"], ["@ghost"])
        self.assertEqual(
            sorted(summary["waiting"]),
            ["@ghost → Platform", "bob@example.com → Platform"],
        )
        self.assertFalse(any(s.startswith("ghost") for s in summary["skipped"]))

        bob = self.invitation("bob@example.com")
        ghost = self.invitation("ghost")
        self.assertEqual((bob["role"], bob["teams"]), ("deployer", ["Platform"]))
        self.assertEqual(
            (ghost["role"], ghost["email"], ghost["host_kind"], ghost["teams"]),
            ("developer", None, "github", ["Platform"]),
        )

        again = self.client.get(
            "/api/v1/import/github/organizations/acme?host=gh", headers=self.h()
        ).json()
        self.assertEqual(
            {p["login"]: p["status"] for p in again["people"]},
            {"ana": "member", "bob": "invited", "ghost": "invited"},
        )

    def test_an_invitee_who_accepts_later_joins_the_mapped_teams(self):
        self.run_import(teams=["platform"], people=["bob"])
        bob = self.invitation("bob@example.com")
        accepted = self.client.post(
            f"/api/auth/invitations/{bob['id']}/accept",
            headers=self.sign_up("Bob", "bob@example.com", bob["id"]),
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)

        teams = self.client.get("/api/v1/teams", headers=self.h()).json()
        self.assertEqual(
            sorted(m["email"] for m in teams[0]["members"]),
            ["ana@example.com", "bob@example.com"],
        )

    def test_a_login_invitation_is_accepted_after_proving_the_login(self):
        self.run_import(
            teams=["platform"], people=["ghost"], people_roles={"ghost": "viewer"}
        )
        ghost = self.invitation("ghost")
        opened = self.client.get(f"/api/auth/invitations/{ghost['id']}").json()
        self.assertEqual(
            (opened["login"], opened["host_kind"], opened["email"]),
            ("ghost", "github", None),
        )
        session = self.sign_up("Ghost", "ghost@elsewhere.dev", ghost["id"])

        plain = self.client.post(
            f"/api/auth/invitations/{ghost['id']}/accept", headers=session
        )
        self.assertEqual(plain.status_code, 400)
        self.assertIn("verify", plain.json()["detail"])

        started = self.client.post(
            f"/api/auth/invitations/{ghost['id']}/verify",
            json={"origin": "https://ap.example.com"},
            headers=session,
        )
        self.assertEqual(started.status_code, 200, started.text)
        url = started.json()["url"]
        self.assertIn("github.com/login/oauth/authorize", url)
        self.assertIn("scope=&", url + "&")
        state = url.split("state=")[1].split("&")[0]

        from urllib.parse import unquote

        state = unquote(state)
        self.assertTrue(state.startswith(f"invite.{ghost['id']}."))

        self.prove("someone-else")
        wrong = self.client.post(
            f"/api/auth/invitations/{ghost['id']}/verify/callback",
            json={"origin": "https://ap.example.com", "code": "c", "state": state},
            headers=session,
        )
        self.assertEqual(wrong.status_code, 400)
        self.assertIn("@ghost", wrong.json()["detail"])

        forged = self.client.post(
            f"/api/auth/invitations/{ghost['id']}/verify/callback",
            json={"origin": "https://ap.example.com", "code": "c", "state": "x.y"},
            headers=session,
        )
        self.assertEqual(forged.status_code, 403)

        self.prove("Ghost")
        joined = self.client.post(
            f"/api/auth/invitations/{ghost['id']}/verify/callback",
            json={"origin": "https://ap.example.com", "code": "c", "state": state},
            headers=session,
        )
        self.assertEqual(joined.status_code, 200, joined.text)

        members = self.client.get("/api/v1/members", headers=self.h()).json()
        self.assertEqual(
            {m["email"]: m["role"] for m in members}["ghost@elsewhere.dev"], "viewer"
        )
        teams = self.client.get("/api/v1/teams", headers=self.h()).json()
        self.assertIn("ghost@elsewhere.dev", [m["email"] for m in teams[0]["members"]])

    def test_role_mapping_is_checked_before_queueing(self):
        for body in (
            {"roles": {"maintainer": "admin"}},
            {"roles": {"org_admin": "owner"}},
            {"people_roles": {"bob": "boss"}},
        ):
            res = self.client.post(
                "/api/v1/import/github",
                json={
                    "host_id": "gh",
                    "organization": "acme",
                    "people": ["bob"],
                    **body,
                },
                headers=self.h(),
            )
            self.assertEqual(res.status_code, 400, (body, res.text))

    def test_an_invitation_can_carry_teams(self):
        team = self.client.post(
            "/api/v1/teams", json={"name": "Ops"}, headers=self.h()
        ).json()
        missing = self.client.post(
            "/api/v1/invitations",
            json={"email": "cy@example.com", "role": "viewer", "team_ids": ["nope"]},
            headers=self.h(),
        )
        self.assertEqual(missing.status_code, 404)
        invited = self.client.post(
            "/api/v1/invitations",
            json={
                "email": "cy@example.com",
                "role": "viewer",
                "team_ids": [team["id"]],
            },
            headers=self.h(),
        ).json()
        self.assertEqual(invited["teams"], ["Ops"])
        accepted = self.client.post(
            f"/api/auth/invitations/{invited['id']}/accept",
            headers=self.sign_up("Cy", "cy@example.com", invited["id"]),
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)
        teams = self.client.get("/api/v1/teams", headers=self.h()).json()
        self.assertEqual([m["email"] for m in teams[0]["members"]], ["cy@example.com"])
