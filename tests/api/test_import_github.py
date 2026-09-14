"""Importing a GitHub organization: repositories → projects and apps, people → members and invitations, teams → teams."""

from __future__ import annotations

from tests.api.test_access import GateCase


class FakeGithub:
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
            {"login": "ana", "name": "Ana", "email": "ana@example.com", "avatar": None},
            {"login": "bob", "name": "Bob", "email": "bob@example.com", "avatar": None},
            {"login": "ghost", "name": "Ghost", "email": None, "avatar": None},
        ]


class GithubImportTest(GateCase):
    def setUp(self):
        super().setUp()
        from action_platform.api.auth.crypto import Sealer
        from action_platform.api.db.models import SourceHost
        from action_platform.api.services.github_import import client, context

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
        self.patch(
            context,
            "repo_from_url",
            lambda url: "acme/web" if url == self.url else None,
        )

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
        from action_platform.api.db.models import Member

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
        from action_platform.api.worker import Worker

        queued = self.client.post(
            "/api/v1/import/github",
            json={
                "host_id": "gh",
                "organization": "acme",
                "repositories": ["acme/web", "acme/broken", "acme/missing"],
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
        self.assertIn("acme/missing: not found on GitHub", summary["skipped"])
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
        from action_platform.api.worker import Worker

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
        from action_platform.api.worker import Worker

        queued = self.client.post(
            "/api/v1/import/github",
            json={"host_id": "gh", "organization": "acme", "projects": [3]},
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
