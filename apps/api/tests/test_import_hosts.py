"""Importing a GitLab group or a Bitbucket workspace: what each directory reads from the host, and the import through the neutral routes."""

from __future__ import annotations

import unittest
from typing import Any

from tests.test_access import GateCase

GITLAB = "https://git.example.com/api/v4"
BITBUCKET = "https://api.bitbucket.org/2.0"


class FakeHttp:
    """Answers each URL (without its paging query) from a table; anything else is a ProviderError like a 404 would be."""

    def __init__(self, table: dict[str, Any]) -> None:
        self.table = table
        self.asked: list[str] = []

    def _answer(self, url: str) -> Any:
        from action_platform.core.exception import ProviderError

        url = url.replace("&per_page=100", "").replace("?per_page=100", "")
        url = url.replace("&page=1", "").replace("?page=1", "")
        self.asked.append(url)

        if url not in self.table:
            raise ProviderError(f"404 {url}")

        return self.table[url]

    def get_json(self, url: str, headers: Any = None) -> Any:
        return self._answer(url)

    def get_pages(self, url: str, headers: Any, limit: int = 20) -> list[Any]:
        return list(self._answer(url))

    def get_values(self, url: str, headers: Any) -> list[Any]:
        return list(self._answer(url))


def gitlab_table(clone: str) -> dict[str, Any]:
    def project(id: int, path: str, archived: bool = False) -> dict:
        return {
            "id": id,
            "path": path.rsplit("/", 1)[-1],
            "path_with_namespace": path,
            "description": None,
            "visibility": "private",
            "archived": archived,
            "default_branch": "main",
            "http_url_to_repo": clone
            if path == "acme/backend/api"
            else f"{GITLAB}/{path}.git",
            "last_activity_at": None,
        }

    return {
        f"{GITLAB}/user": {"id": 1, "username": "ana", "name": "Ana"},
        f"{GITLAB}/groups?min_access_level=10&top_level_only=true&order_by=path": [
            {"id": 10, "full_path": "acme", "full_name": "Acme"}
        ],
        f"{GITLAB}/groups/acme?with_projects=false": {"id": 10, "full_path": "acme"},
        f"{GITLAB}/groups/10/projects?include_subgroups=true&with_shared=false": [
            project(100, "acme/site"),
            project(101, "acme/backend/api"),
            project(102, "acme/backend/jobs/worker", archived=True),
        ],
        f"{GITLAB}/groups/10/descendant_groups?order_by=path": [
            {
                "id": 11,
                "full_path": "acme/backend",
                "description": "APIs",
                "web_url": "https://git.example.com/groups/acme/backend",
            },
            {"id": 12, "full_path": "acme/backend/jobs", "description": ""},
        ],
        f"{GITLAB}/groups/11/members": [{"username": "bob"}, {"username": "cy"}],
        f"{GITLAB}/groups/12/members": [{"username": "cy"}],
        f"{GITLAB}/groups/10/members/all": [
            {"id": 1, "username": "ana", "name": "Ana", "access_level": 50},
            {"id": 2, "username": "bob", "name": "Bob", "access_level": 40},
            {"id": 3, "username": "cy", "name": "Cy", "access_level": 30},
            {
                "id": 4,
                "username": "bot",
                "name": "Bot",
                "access_level": 30,
                "bot": True,
            },
        ],
        f"{GITLAB}/users/1": {"public_email": "ana@example.com"},
        f"{GITLAB}/users/2": {"public_email": "bob@example.com"},
        f"{GITLAB}/users/3": {"public_email": ""},
    }


def bitbucket_table() -> dict[str, Any]:
    def repo(slug: str, project: str) -> dict:
        return {
            "full_name": f"acme/{slug}",
            "slug": slug,
            "description": "",
            "is_private": True,
            "language": "python",
            "mainbranch": {"name": "develop"},
            "updated_on": None,
            "project": {"key": project},
            "links": {
                "clone": [
                    {
                        "name": "https",
                        "href": f"https://ana@bitbucket.org/acme/{slug}.git",
                    },
                    {"name": "ssh", "href": f"git@bitbucket.org:acme/{slug}.git"},
                ]
            },
        }

    return {
        f"{BITBUCKET}/user": {"username": "ana-u", "nickname": "ana"},
        f"{BITBUCKET}/user/permissions/workspaces?pagelen=100": [
            {"workspace": {"slug": "acme", "name": "Acme"}},
            {"workspace": {"slug": "ana", "name": "Ana"}},
        ],
        f"{BITBUCKET}/repositories/acme?pagelen=100": [
            repo("web", "SHOP"),
            repo("tools", "OPS"),
        ],
        f"{BITBUCKET}/workspaces/acme/projects?pagelen=100": [
            {"key": "SHOP", "name": "Shop", "description": "Storefront"},
            {"key": "OPS", "name": "Ops"},
        ],
        f"{BITBUCKET}/workspaces/acme/permissions?pagelen=100": [
            {"permission": "owner", "user": {"uuid": "{a}"}},
            {"permission": "member", "user": {"uuid": "{b}"}},
        ],
        f"{BITBUCKET}/workspaces/acme/members?pagelen=100": [
            {"user": {"uuid": "{a}", "nickname": "ana", "display_name": "Ana"}},
            {"user": {"uuid": "{b}", "nickname": "bob", "display_name": "Bob"}},
        ],
    }


def creds(kind: str, base_url: str | None = None, username: str | None = None):
    from app.core.shared.credentials import Credentials

    return Credentials(
        kind=kind, token="t", base_url=base_url, username=username, owner=None
    )


class GitlabDirectoryTest(unittest.TestCase):
    def setUp(self):
        from app.services.projects.organization_import import gitlab

        self.http = FakeHttp(gitlab_table("file:///nowhere/api.git"))
        self.original = gitlab.http
        gitlab.http = self.http
        self.directory = gitlab.GitlabDirectory(
            creds("gitlab", "https://git.example.com")
        )

    def tearDown(self):
        from app.services.projects.organization_import import gitlab

        gitlab.http = self.original

    def test_reads_a_self_hosted_group_with_its_subgroups(self):
        d = self.directory
        self.assertEqual(
            [(o["login"], o["kind"]) for o in d.organizations()],
            [("ana", "user"), ("acme", "org")],
        )
        self.assertEqual(
            [
                (r["full_name"], r["name"], r["archived"])
                for r in d.repositories("acme")
            ],
            [
                ("acme/site", "site", False),
                ("acme/backend/api", "api", False),
                ("acme/backend/jobs/worker", "worker", True),
            ],
        )
        self.assertEqual(
            [(p["number"], p["title"], p["repositories"]) for p in d.projects("acme")],
            [
                (11, "backend", ["acme/backend/api"]),
                (12, "backend/jobs", ["acme/backend/jobs/worker"]),
            ],
        )
        self.assertEqual(
            [(t["slug"], t["members"], t["repositories"]) for t in d.teams("acme")],
            [
                (
                    "backend",
                    ["bob", "cy"],
                    ["acme/backend/api", "acme/backend/jobs/worker"],
                ),
                ("backend-jobs", ["cy"], ["acme/backend/jobs/worker"]),
            ],
        )
        self.assertEqual(
            [(p["login"], p["email"], p["role"]) for p in d.people("acme")],
            [
                ("ana", "ana@example.com", "org_admin"),
                ("bob", "bob@example.com", "team_maintainer"),
                ("cy", None, "member"),
            ],
        )
        self.assertTrue(all(u.startswith(GITLAB) for u in self.http.asked))

    def test_gitlab_com_without_a_base_url(self):
        from app.services.projects.organization_import import gitlab

        self.assertEqual(
            gitlab.GitlabDirectory(creds("gitlab")).api, "https://gitlab.com/api/v4"
        )
        self.assertEqual(
            gitlab.GitlabDirectory(
                creds("gitlab", "https://git.example.com/api/v4/")
            ).api,
            GITLAB,
        )


class BitbucketDirectoryTest(unittest.TestCase):
    def setUp(self):
        from app.services.projects.organization_import import bitbucket

        self.original = bitbucket.http
        bitbucket.http = FakeHttp(bitbucket_table())
        self.directory = bitbucket.BitbucketDirectory(creds("bitbucket"))

    def tearDown(self):
        from app.services.projects.organization_import import bitbucket

        bitbucket.http = self.original

    def test_reads_a_workspace(self):
        d = self.directory
        self.assertEqual(
            [(o["login"], o["kind"]) for o in d.organizations()],
            [("ana", "user"), ("acme", "org")],
        )
        web = d.repositories("acme")[0]
        self.assertEqual(
            (web["full_name"], web["url"], web["default_branch"], web["language"]),
            ("acme/web", "https://bitbucket.org/acme/web.git", "develop", "python"),
        )
        self.assertEqual(
            [(p["number"], p["title"], p["repositories"]) for p in d.projects("acme")],
            [("SHOP", "Shop", ["acme/web"]), ("OPS", "Ops", ["acme/tools"])],
        )
        self.assertEqual(d.teams("acme"), [])
        self.assertEqual(
            [(p["login"], p["email"], p["role"]) for p in d.people("acme")],
            [("ana", None, "org_admin"), ("bob", None, "member")],
        )
        self.assertTrue(d.limits)

    def test_an_app_password_authenticates_with_basic_auth(self):
        from app.services.projects.organization_import import bitbucket

        d = bitbucket.BitbucketDirectory(creds("bitbucket", username="ana"))
        self.assertTrue(d.headers["authorization"].startswith("Basic "))


class NeutralImportTest(GateCase):
    def setUp(self):
        super().setUp()
        from app.core.auth.crypto import Sealer
        from app.core.db.models import SourceHost
        from app.services.projects.organization_import import (
            bitbucket,
            context,
            gitlab,
        )

        sealer = Sealer(self.app.state.secrets)

        with self.app.state.db.session() as s:
            s.add(
                SourceHost(
                    id="gl",
                    organization_id=self.org["id"],
                    kind="gitlab",
                    name="GitLab",
                    base_url="https://git.example.com",
                    token_encrypted=sealer.seal("t"),
                )
            )
            s.add(
                SourceHost(
                    id="bb",
                    organization_id=self.org["id"],
                    kind="bitbucket",
                    name="Bitbucket",
                    token_encrypted=sealer.seal("t"),
                )
            )

        self.patch(gitlab, "http", FakeHttp(gitlab_table(self.url)))
        self.patch(bitbucket, "http", FakeHttp(bitbucket_table()))
        url = self.url

        class KnownUrl:
            def __init__(self, value):
                self.value = value

            @property
            def path(self):
                return "acme/backend/api" if self.value == url else None

        self.patch(context, "GitUrl", KnownUrl)

    def test_previews_a_bitbucket_workspace_with_its_limits(self):
        orgs = self.client.get(
            "/api/v1/import/bb/organizations", headers=self.h()
        ).json()
        self.assertEqual([o["login"] for o in orgs["organizations"]], ["ana", "acme"])
        self.assertIsNone(orgs["install_url"])

        preview = self.client.get(
            "/api/v1/import/bb/organizations/acme", headers=self.h()
        ).json()
        self.assertEqual(preview["host_kind"], "bitbucket")
        self.assertEqual([p["number"] for p in preview["projects"]], ["SHOP", "OPS"])
        self.assertEqual(preview["teams"], [])
        self.assertEqual(
            {p["login"]: p["status"] for p in preview["people"]},
            {"ana": "no_email", "bob": "no_email"},
        )
        self.assertTrue(any("email" in limit for limit in preview["limits"]))

    def test_imports_a_gitlab_subgroup_as_a_project_with_its_team(self):
        from app.services.jobs.worker import Worker

        preview = self.client.get(
            "/api/v1/import/gl/organizations/acme", headers=self.h()
        )
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(
            {p["login"]: (p["status"], p["role"]) for p in preview.json()["people"]},
            {
                "ana": ("member", "org_admin"),
                "bob": ("invitable", "team_maintainer"),
                "cy": ("no_email", "member"),
            },
        )

        queued = self.client.post(
            "/api/v1/import",
            json={
                "host_id": "gl",
                "organization": "acme",
                "projects": [{"number": 11}],
                "teams": ["backend"],
                "people": ["bob"],
                "roles": {"team_maintainer": "deployer"},
            },
            headers=self.h(),
        )
        self.assertEqual(queued.status_code, 202, queued.text)
        Worker(self.app.state.db, self.app.state.secrets, "test").run(once=True)
        done = self.client.get(
            f"/api/v1/jobs/{queued.json()['job']}", headers=self.h()
        ).json()
        self.assertEqual(done["kind"], "import_organization")
        self.assertEqual(done["status"], "done", done)
        summary = done["result"]
        self.assertEqual(summary["projects"], ["backend"])
        self.assertEqual(summary["apps"], ["api → backend"])
        self.assertEqual(summary["teams"], ["backend"])
        self.assertEqual(summary["invitations"], ["bob@example.com"])
        self.assertEqual(summary["waiting"], ["bob@example.com → backend"])

        projects = self.client.get("/api/v1/projects", headers=self.h()).json()
        self.assertEqual([p["name"] for p in projects], ["backend"])
        self.assertEqual([a["name"] for a in projects[0]["apps"]], ["api"])
        self.assertEqual(projects[0]["team"]["name"], "backend")

        again = self.client.get(
            "/api/v1/import/gl/organizations/acme", headers=self.h()
        ).json()
        self.assertEqual(
            {r["full_name"]: r["imported_as"] for r in again["repositories"]},
            {
                "acme/site": None,
                "acme/backend/api": "backend",
                "acme/backend/jobs/worker": None,
            },
        )

    def test_a_subgroup_login_with_a_slash_reaches_the_preview(self):
        from app.services.projects.organization_import import gitlab

        table = gitlab_table(self.url)
        table[f"{GITLAB}/groups/acme%2Fbackend?with_projects=false"] = {
            "id": 11,
            "full_path": "acme/backend",
        }
        table[
            f"{GITLAB}/groups/11/projects?include_subgroups=true&with_shared=false"
        ] = []
        table[f"{GITLAB}/groups/11/descendant_groups?order_by=path"] = []
        table[f"{GITLAB}/groups/11/members/all"] = []
        self.patch(gitlab, "http", FakeHttp(table))

        preview = self.client.get(
            "/api/v1/import/gl/organizations/acme/backend", headers=self.h()
        )
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(preview.json()["organization"], "acme/backend")

    def test_the_github_routes_stay(self):
        self.assertEqual(
            self.client.get(
                "/api/v1/import/github/organizations?host=gl", headers=self.h()
            ).status_code,
            200,
        )

    def test_a_bitbucket_invitee_proves_the_nickname_the_workspace_lists(self):
        from urllib.parse import unquote

        from app.services.integrations.hosts import bitbucket as provider
        from app.services.jobs.worker import Worker
        from app.services.organization import invitations

        self.setenv("AP_BITBUCKET_CLIENT_ID", "cid")
        self.setenv("AP_BITBUCKET_CLIENT_SECRET", "csecret")
        queued = self.client.post(
            "/api/v1/import",
            json={"host_id": "bb", "organization": "acme", "people": ["bob"]},
            headers=self.h(),
        )
        self.assertEqual(queued.status_code, 202, queued.text)
        Worker(self.app.state.db, self.app.state.secrets, "test").run(once=True)
        done = self.client.get(
            f"/api/v1/jobs/{queued.json()['job']}", headers=self.h()
        ).json()
        self.assertEqual(done["result"]["login_invitations"], ["@bob"])

        invitation = self.client.get("/api/v1/invitations", headers=self.h()).json()[0]
        self.assertEqual(
            (invitation["login"], invitation["host_kind"]), ("bob", "bitbucket")
        )
        signed = self.client.post(
            "/api/auth/sign-up",
            json={
                "name": "Bob",
                "email": "bob@elsewhere.dev",
                "password": "password1",
                "invitation_id": invitation["id"],
            },
        ).json()
        session = {"X-Session-Token": signed["session"]["token"]}
        url = self.client.post(
            f"/api/auth/invitations/{invitation['id']}/verify",
            json={"origin": "https://ap.example.com"},
            headers=session,
        ).json()["url"]
        state = unquote(url.split("state=")[1].split("&")[0])

        self.patch(
            provider.BitbucketProvider,
            "exchange_code",
            lambda self, app, origin, code: ("tok", None, None),
        )
        self.patch(
            provider.BitbucketProvider,
            "identity",
            lambda self, app, token: ("bob-account", "Bob"),
        )
        self.patch(
            invitations,
            "http",
            FakeHttp(
                {f"{BITBUCKET}/user": {"username": "bob-account", "nickname": "bob"}}
            ),
        )
        joined = self.client.post(
            f"/api/auth/invitations/{invitation['id']}/verify/callback",
            json={"origin": "https://ap.example.com", "code": "c", "state": state},
            headers=session,
        )
        self.assertEqual(joined.status_code, 200, joined.text)
