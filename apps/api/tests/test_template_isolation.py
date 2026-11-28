from __future__ import annotations

from action_platform.core.exception import TemplateError
from action_platform.core.flow import git as core_git
from action_platform.core.scaffold import sources as core_sources
from action_platform.core.scaffold.sources import LocalTemplateStore, TemplateSource
from action_platform.testing.fixtures import git, template_repo

from tests.test_access import GateCase

TOKEN_A = "tok-a"


class TemplateIsolationCase(GateCase):
    def setUp(self):
        super().setUp()
        self.cache = self.tmp_path / "cache"
        self.setenv(
            "ACTION_PLATFORM_TEMPLATES", str(template_repo(self.tmp_path / "official"))
        )
        self.patch(core_sources, "CACHE", self.cache)
        self.private = self.tmp_path / "private-templates"
        self.private.mkdir()
        git(self.private, "init", "-q", "-b", "main")
        (self.private / "pyproject.toml").write_text('[project]\nname = "secret"\n')
        (self.private / "SECRET.md").write_text("org a only\n")
        git(self.private, "add", "-A")
        git(
            self.private,
            "-c",
            "user.name=a",
            "-c",
            "user.email=a@example.com",
            "commit",
            "-q",
            "-m",
            "init",
        )
        self.private_url = self.private.as_uri()
        original = LocalTemplateStore._git

        def private_host(*args: str) -> None:
            reaches = "clone" in args or "fetch" in args
            token = (core_git.AUTH_ENV.get() or {}).get("AP_GIT_TOKEN")

            if reaches and token != TOKEN_A:
                raise TemplateError("Authentication failed")

            original(*args)

        self.patch(LocalTemplateStore, "_git", staticmethod(private_host))
        self.source_id = self.add_private_source()
        self.other = self.second_organization()

    def add_private_source(self) -> str:
        from app.core.db.models import SourceHost, TemplateSource as Row

        res = self.client.post(
            "/api/v1/template-sources",
            json={"name": "private", "url": self.private_url, "ref": "main"},
            headers=self.h(),
        )
        assert res.status_code == 201, res.text
        with self.app.state.db.session() as s:
            s.add(
                SourceHost(
                    id="h-a",
                    organization_id=self.org["id"],
                    kind="github",
                    name="GitHub",
                    auth_kind="token",
                    token_encrypted=self.app.state.sealer.seal(TOKEN_A),
                )
            )
            s.get(Row, res.json()["id"]).source_host_id = "h-a"
        return res.json()["id"]

    def second_organization(self) -> dict:
        from datetime import timedelta

        from app.core.db.models import Invitation, Member
        from app.services.auth.service import now

        with self.app.state.db.session() as s:
            s.add(
                Invitation(
                    id="i-bia",
                    organization_id=self.org["id"],
                    email="bia@example.com",
                    role="viewer",
                    status="pending",
                    expires_at=now() + timedelta(days=1),
                    inviter_id=self.user_id,
                )
            )
        signed = self.client.post(
            "/api/auth/sign-up",
            json={
                "name": "Bia",
                "email": "bia@example.com",
                "password": "password1",
                "invitation_id": "i-bia",
            },
        )
        assert signed.status_code == 201, signed.text
        session = signed.json()["session"]["token"]
        org = self.client.post(
            "/api/auth/organizations",
            json={"name": "Beta", "slug": "beta"},
            headers=self.h(session),
        ).json()
        with self.app.state.db.session() as s:
            s.query(Member).filter(
                Member.organization_id == self.org["id"],
                Member.user_id == signed.json()["user"]["id"],
            ).delete()
        return {"session": session, "org": org}

    def hb(self) -> dict:
        return self.h(self.other["session"])

    def owned_cache(self, organization_id: str) -> TemplateSource:
        return TemplateSource(url=self.private_url, ref="main", owner=organization_id)

    def matrix(self, headers: dict) -> dict:
        res = self.client.get("/api/v1/matrix", headers=headers)
        assert res.status_code == 200, res.text
        return res.json()

    def private_projects(self, matrix: dict) -> list[dict]:
        return [p for p in matrix["projects"] if p["source"] != "official"]

    def register_in(self, organization_id: str, project_id: str, app_id: str) -> str:
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
                Project(
                    id=project_id,
                    organization_id=organization_id,
                    name=project_id,
                    slug=project_id,
                )
            )
            s.add(
                App(
                    id=app_id,
                    project_id=project_id,
                    registry_id=registry_id,
                    name=app_id,
                )
            )
        return registry_id

    def warm_cache_as_owner(self) -> None:
        mine = self.matrix(self.h())
        status = next(s for s in mine["sources"] if s["name"] == "private")
        self.assertTrue(status["ok"], status)
        self.assertEqual(len(self.private_projects(mine)), 1)
        self.assertTrue(self.owned_cache(self.org["id"]).cache.exists())


class CacheTest(TemplateIsolationCase):
    def test_clones_of_the_same_url_live_apart_per_organization(self):
        a = self.owned_cache(self.org["id"]).cache
        b = self.owned_cache(self.other["org"]["id"]).cache
        self.assertNotEqual(a, b)
        self.assertNotEqual(a.parent, b.parent)
        self.assertFalse(b.is_relative_to(a.parent))

    def test_another_organization_adding_the_same_url_gets_no_clone(self):
        self.warm_cache_as_owner()
        added = self.client.post(
            "/api/v1/template-sources",
            json={"name": "copied", "url": self.private_url, "ref": "main"},
            headers=self.hb(),
        )
        self.assertEqual(added.status_code, 201, added.text)

        theirs = self.matrix(self.hb())

        status = next(s for s in theirs["sources"] if s["name"] == "copied")
        self.assertFalse(status["ok"])
        self.assertEqual(self.private_projects(theirs), [])
        self.assertFalse(self.owned_cache(self.other["org"]["id"]).cache.exists())
        self.assertTrue(self.owned_cache(self.org["id"]).cache.exists())

    def test_resolving_without_the_owner_never_reads_its_clone(self):
        from app.schemas import SourceSpec
        from app.services.templates import TemplateRepos

        self.warm_cache_as_owner()
        spec = SourceSpec(
            name="private",
            url=self.private_url,
            ref="main",
            organization_id=self.other["org"]["id"],
        )

        with self.assertRaises(TemplateError):
            TemplateRepos.resolve(spec)

        with self.assertRaises(TemplateError):
            TemplateRepos.resolve(spec.model_copy(update={"organization_id": None}))


class CrossOrganizationRoutesTest(TemplateIsolationCase):
    def test_list_shows_only_the_callers_sources(self):
        self.warm_cache_as_owner()
        listed = self.client.get("/api/v1/template-sources", headers=self.hb())
        self.assertEqual(listed.json(), [])
        theirs = self.matrix(self.hb())
        self.assertEqual([s["name"] for s in theirs["sources"]], ["official"])
        self.assertEqual(self.private_projects(theirs), [])

    def test_a_source_by_name_of_another_organization_is_not_found(self):
        from app.core.db.models import Project

        self.warm_cache_as_owner()
        with self.app.state.db.session() as s:
            s.add(
                Project(
                    id="pb",
                    organization_id=self.other["org"]["id"],
                    name="B",
                    slug="b",
                )
            )
        res = self.client.post(
            "/api/v1/projects/pb/apps/init",
            json={
                "type": "web",
                "stack": "python",
                "name": "stolen",
                "push": False,
                "template_source": "private",
            },
            headers=self.hb(),
        )
        self.assertEqual(res.status_code, 400, res.text)
        self.assertIn("not found", res.text)

    def test_init_with_the_owners_url_is_refused(self):
        self.warm_cache_as_owner()
        for source in (
            {"name": "private", "url": self.private_url, "ref": "main"},
            {"name": "anything", "url": self.private_url},
            "private",
        ):
            res = self.client.post(
                "/api/v1/apps/init",
                json={
                    "type": "web",
                    "stack": "python",
                    "name": "stolen",
                    "push": False,
                    "source": source,
                },
                headers=self.hb(),
            )
            self.assertEqual(res.status_code, 400, (source, res.text))
            self.assertIn("not found", res.text)

    def test_cloud_and_services_with_the_owners_url_are_refused(self):
        self.warm_cache_as_owner()
        registry_id = self.register_in(self.other["org"]["id"], "pb", "ab")
        source = {"name": "private", "url": self.private_url, "ref": "main"}

        cloud = self.client.put(
            f"/api/v1/apps/{registry_id}/cloud",
            json={"target": "docker", "source": source},
            headers=self.hb(),
        )
        services = self.client.post(
            f"/api/v1/apps/{registry_id}/services",
            json={"name": "postgres", "source": source},
            headers=self.hb(),
        )

        for res in (cloud, services):
            self.assertEqual(res.status_code, 400, res.text)
            self.assertIn("not found", res.text)

    def test_a_registered_name_with_another_url_is_refused(self):
        registry_id = self.register_in(self.org["id"], "pa", "aa")
        res = self.client.post(
            f"/api/v1/apps/{registry_id}/cloud",
            json={
                "target": "docker",
                "source": {"name": "private", "url": "https://example.com/x.git"},
            },
            headers=self.h(),
        )
        self.assertEqual(res.status_code, 400, res.text)
        self.assertIn("not found", res.text)


class RevocationTest(TemplateIsolationCase):
    def test_removing_the_source_deletes_its_clone_and_its_templates(self):
        self.warm_cache_as_owner()
        removed = self.client.delete(
            f"/api/v1/template-sources/{self.source_id}", headers=self.h()
        )
        self.assertEqual(removed.status_code, 204, removed.text)
        self.assertFalse(self.owned_cache(self.org["id"]).cache.exists())
        self.assertEqual(self.private_projects(self.matrix(self.h())), [])
        res = self.client.post(
            "/api/v1/apps/init",
            json={
                "type": "web",
                "stack": "python",
                "name": "late",
                "push": False,
                "source": "private",
            },
            headers=self.h(),
        )
        self.assertEqual(res.status_code, 400, res.text)

    def test_removing_the_host_revokes_the_clone(self):
        self.warm_cache_as_owner()
        removed = self.client.delete("/api/v1/hosts/h-a", headers=self.h())
        self.assertEqual(removed.status_code, 204, removed.text)
        self.assertFalse(self.owned_cache(self.org["id"]).cache.exists())

        mine = self.matrix(self.h())

        status = next(s for s in mine["sources"] if s["name"] == "private")
        self.assertFalse(status["ok"])
        self.assertEqual(self.private_projects(mine), [])

    def test_a_refresh_that_loses_access_drops_the_clone(self):
        from app.core.db.models import SourceHost

        self.warm_cache_as_owner()
        with self.app.state.db.session() as s:
            s.get(SourceHost, "h-a").token_encrypted = self.app.state.sealer.seal(
                "revoked"
            )

        mine = self.matrix(self.h())

        status = next(s for s in mine["sources"] if s["name"] == "private")
        self.assertFalse(status["ok"])
        self.assertEqual(self.private_projects(mine), [])
        self.assertFalse(self.owned_cache(self.org["id"]).cache.exists())

    def test_deleting_the_organization_deletes_its_clones(self):
        self.warm_cache_as_owner()
        owner_dir = TemplateSource.owner_cache(self.org["id"])
        self.assertTrue(owner_dir.exists())
        res = self.client.delete(
            f"/api/v1/organizations/{self.org['id']}",
            params={"confirm": "acme"},
            headers=self.h(),
        )
        self.assertEqual(res.status_code, 204, res.text)
        self.assertFalse(owner_dir.exists())
