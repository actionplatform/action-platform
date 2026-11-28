"""The remote MCP tools against the real API: the Remote client's requests go through a TestClient, so every tool meets the gate, the routes and their permission checks."""

from __future__ import annotations

import asyncio
import io
import json
import unittest
import urllib.error
from typing import Any

from tests.test_access import GateCase

try:
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:
    ToolError = None

SERVER = "http://testserver"
FULL = "read,write,release,admin"


class Answer:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> "Answer":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None


@unittest.skipUnless(ToolError, "mcp is not installed")
class RemoteToolsCase(GateCase):
    def setUp(self):
        super().setUp()
        from action_platform.remote import client

        def urlopen(req, timeout=None):
            res = self.client.request(
                req.get_method(),
                req.full_url.removeprefix(SERVER),
                content=req.data,
                headers=dict(req.header_items()),
            )

            if res.status_code >= 400:
                raise urllib.error.HTTPError(
                    req.full_url,
                    res.status_code,
                    res.reason_phrase,
                    res.headers,
                    io.BytesIO(res.content),
                )

            return Answer(res.content)

        self.patch(client.destination, "urlopen", urlopen)

    def server(self, scope: str = FULL, token: str | None = None):
        from action_platform.mcp.server import REMOTE_INSTRUCTIONS, MCPServer
        from action_platform.mcp.tools import remote as remote_tools
        from action_platform.remote.client import Remote

        server = MCPServer("action-platform", instructions=REMOTE_INSTRUCTIONS)
        self.remote = Remote(SERVER, token or self.token(scope))
        remote_tools.register(server, self.remote)

        return server

    def call(self, server, tool: str, **args: Any) -> Any:
        result = asyncio.run(server.call_tool(tool, args))

        if result.structured_content:
            content = result.structured_content

            return content["result"] if set(content) == {"result"} else content

        return json.loads(result.content[0].text)

    def refused(self, server, tool: str, **args: Any) -> str:
        with self.assertRaises(ToolError) as caught:
            asyncio.run(server.call_tool(tool, args))

        return str(caught.exception)

    def join(self, email: str, role: str = "developer") -> str:
        invited = self.client.post(
            "/api/v1/invitations",
            json={"email": email, "role": role},
            headers=self.h(),
        ).json()
        signed = self.client.post(
            "/api/auth/sign-up",
            json={
                "name": email.split("@")[0],
                "email": email,
                "password": "password1",
                "invitation_id": invited["id"],
            },
        ).json()
        accepted = self.client.post(
            f"/api/auth/invitations/{invited['id']}/accept",
            headers={"X-Session-Token": signed["session"]["token"]},
        )
        assert accepted.status_code == 200, accepted.text

        return signed["user"]["id"]


class InvitationToolsTest(RemoteToolsCase):
    def test_invite_list_and_cancel(self):
        server = self.server()

        sent = self.call(
            server, "invite_member", email="Bob@example.com", role="deployer"
        )

        self.assertEqual((sent["email"], sent["role"]), ("bob@example.com", "deployer"))
        self.assertEqual(sent["link"], f"{SERVER}/invite/{sent['id']}")
        (row,) = self.call(server, "list_invitations")
        self.assertEqual(row["id"], sent["id"])
        self.assertEqual(row["inviter"], "Ana")
        self.assertEqual(
            self.call(server, "cancel_invitation", id=sent["id"]), {"ok": True}
        )
        self.assertEqual(self.call(server, "list_invitations"), [])

    def test_a_role_outside_the_list_never_reaches_the_platform(self):
        server = self.server()

        self.assertIn(
            "role", self.refused(server, "invite_member", email="b@x.io", role="god")
        )
        self.assertEqual(self.call(server, "list_invitations"), [])

    def test_a_token_without_admin_scope_is_refused(self):
        server = self.server("read,write,release")

        for tool, args in (
            ("list_invitations", {}),
            ("invite_member", {"email": "b@x.io", "role": "viewer"}),
            ("cancel_invitation", {"id": "nope"}),
        ):
            with self.subTest(tool=tool):
                self.assertIn("org.manage", self.refused(server, tool, **args))

    def test_a_developer_is_refused(self):
        self.join("dev@example.com")
        dev = self.client.post(
            "/api/auth/sign-in",
            json={"email": "dev@example.com", "password": "password1"},
        ).json()["session"]["token"]
        minted = self.client.post(
            "/api/v1/tokens",
            json={"scope": "read,write", "name": "t"},
            headers=self.h(dev),
        ).json()["token"]
        server = self.server(token=minted)

        self.assertIn(
            "lacks org.manage",
            self.refused(server, "invite_member", email="c@x.io", role="viewer"),
        )


class OwnerInvitationTest(RemoteToolsCase):
    def test_only_an_owner_invites_an_owner(self):
        self.join("bob@example.com", role="admin")
        bob = self.client.post(
            "/api/auth/sign-in",
            json={"email": "bob@example.com", "password": "password1"},
        ).json()["session"]["token"]
        minted = self.client.post(
            "/api/v1/tokens", json={"scope": FULL, "name": "t"}, headers=self.h(bob)
        ).json()["token"]

        self.assertIn(
            "only an owner",
            self.refused(
                self.server(token=minted),
                "invite_member",
                email="bob+2@example.com",
                role="owner",
            ),
        )
        self.assertEqual(
            self.call(self.server(), "invite_member", email="c@x.io", role="owner")[
                "role"
            ],
            "owner",
        )


class MemberRemovalToolsTest(RemoteToolsCase):
    def test_remove_from_a_team_then_from_the_organization(self):
        bob = self.join("bob@example.com")
        server = self.server()
        team = self.call(server, "create_team", name="Core")
        self.call(server, "add_team_member", team_id=team["id"], user_id=bob)

        self.assertEqual(
            self.call(server, "remove_team_member", team_id=team["id"], user_id=bob),
            {"ok": True},
        )
        (row,) = self.call(server, "list_teams")
        self.assertEqual(row["members"], [])
        self.assertEqual(self.call(server, "remove_member", user_id=bob), {"ok": True})
        self.assertEqual(
            [m["email"] for m in self.call(server, "list_members")],
            ["ana@example.com"],
        )

    def test_only_an_owner_removes_an_owner(self):
        bob = self.join("bob@example.com", role="admin")
        bob_session = self.client.post(
            "/api/auth/sign-in",
            json={"email": "bob@example.com", "password": "password1"},
        ).json()["session"]["token"]
        minted = self.client.post(
            "/api/v1/tokens",
            json={"scope": FULL, "name": "t"},
            headers=self.h(bob_session),
        ).json()["token"]
        server = self.server(token=minted)

        self.assertIn(
            "only an owner",
            self.refused(server, "remove_member", user_id=self.user_id),
        )
        self.assertNotEqual(bob, self.user_id)

    def test_a_token_without_admin_scope_is_refused(self):
        bob = self.join("bob@example.com")
        server = self.server("read,write,release")

        self.assertIn("org.manage", self.refused(server, "remove_member", user_id=bob))
        self.assertIn(
            "org.manage",
            self.refused(server, "remove_team_member", team_id="t", user_id=bob),
        )


class PluginOptionsClientTest(RemoteToolsCase):
    def test_round_trip_through_the_public_methods(self):
        from action_platform.remote.client import Remote

        remote = Remote(SERVER, self.token(FULL))

        saved = remote.set_plugin_options("aws-lambda", {"region": "us-east-1"})

        self.assertEqual(saved.options, {"region": "us-east-1"})
        self.assertEqual(remote.plugin_options("aws-lambda").options, saved.options)

    def test_a_slug_the_image_does_not_run_is_refused(self):
        from action_platform.remote.client import Remote, RemoteError

        remote = Remote(SERVER, self.token(FULL))

        for call in (
            lambda: remote.plugin_options("nope"),
            lambda: remote.set_plugin_options("nope", {"api_key": "x"}),
        ):
            with self.assertRaises(RemoteError) as caught:
                call()

            self.assertEqual(caught.exception.status, 404)
            self.assertIn("nope", caught.exception.detail)


class AppToolsCase(RemoteToolsCase):
    def setUp(self):
        super().setUp()
        self.registry_id = self.register()


class ScopeToolsTest(AppToolsCase):
    def test_update_keeps_what_is_not_given_and_delete_removes(self):
        self.scopes("dev", "prod")
        server = self.server()

        updated = self.call(
            server,
            "update_scope",
            id=self.registry_id,
            name="prod",
            criticality="critical",
        )
        self.assertEqual(
            {s["name"]: (s["kind"], s["criticality"]) for s in updated["items"]},
            {"dev": ("web", "test"), "prod": ("web", "critical")},
        )

        left = self.call(server, "delete_scope", id=self.registry_id, name="dev")
        self.assertEqual([s["name"] for s in left["items"]], ["prod"])

    def test_a_read_only_token_cannot_change_scopes(self):
        self.scopes("prod")
        server = self.server("read")

        for tool, args in (
            ("update_scope", {"name": "prod", "criticality": "low"}),
            ("delete_scope", {"name": "prod"}),
        ):
            with self.subTest(tool=tool):
                self.assertIn(
                    "app.configure",
                    self.refused(server, tool, id=self.registry_id, **args),
                )


class ReadinessAndJobToolsTest(AppToolsCase):
    def setUp(self):
        super().setUp()
        from app.core.db.models import Release
        from app.repositories.releases import ReadinessStore, ReleaseStore

        from action_platform.core.context import Check

        self.scopes("dev", "prod")

        with self.app.state.db.session() as s:
            release = ReleaseStore(s).ensure("a1", "v1.2.3", "git")
            s.flush()
            ReadinessStore(s).done(
                s.get(Release, release.id),
                "prod",
                [
                    Check(
                        "aws.permissions",
                        False,
                        "may not lambda:GetLayerVersion",
                        fix="grant it",
                    )
                ],
                "j0",
            )

    def test_readiness_shows_the_checks_the_web_shows(self):
        server = self.server()

        (row,) = self.call(
            server, "release_readiness", id=self.registry_id, tag="1.2.3", scope="prod"
        )

        self.assertEqual((row["stage"], row["verdict"]), ("prod", "blocked"))
        self.assertEqual(row["checks"][0]["id"], "aws.permissions")
        self.assertEqual(row["checks"][0]["fix"], "grant it")
        self.assertEqual(
            self.call(
                server,
                "release_readiness",
                id=self.registry_id,
                tag="v1.2.3",
                scope="dev",
            ),
            [],
        )

    def test_recheck_queues_a_job_the_job_tools_follow(self):
        server = self.server()

        queued = self.call(
            server, "recheck_readiness", id=self.registry_id, tag="v1.2.3", scope="dev"
        )
        (job_id,) = queued["jobs"]

        self.assertEqual(
            self.call(server, "job_status", job_id=job_id)["kind"], "readiness"
        )
        logs = self.call(server, "job_logs", job_id=job_id)
        self.assertEqual((logs["lines"], logs["finished"]), ([], False))

    def test_recheck_needs_app_release(self):
        server = self.server("read,write")

        self.assertIn(
            "app.release",
            self.refused(
                server, "recheck_readiness", id=self.registry_id, tag="v1.2.3"
            ),
        )

    def test_a_blocked_release_is_refused_by_deploy(self):
        server = self.server()

        self.assertIn(
            "not deployable to prod",
            self.refused(
                server,
                "deploy",
                id=self.registry_id,
                stage="prod",
                version="1.2.3",
                dry_run=False,
                background=True,
            ),
        )

    def test_a_background_deploy_answers_with_a_job_whose_log_can_be_followed(self):
        from action_platform.logging import emit
        from app.services.jobs import registry
        from app.services.jobs.worker import Worker

        server = self.server()

        queued = self.call(
            server,
            "deploy",
            id=self.registry_id,
            stage="dev",
            version="1.2.3",
            dry_run=False,
            background=True,
        )
        self.assertEqual(queued["status"], "queued")

        def fake(payload):
            emit("$ sam deploy")
            emit("Successfully created/updated stack")

            return {"ok": True}

        original = registry._factories["deploy"]
        registry.register("deploy", lambda s: fake)

        try:
            Worker(self.app.state.db, self.app.state.secrets, "test").run(once=True)
        finally:
            registry.register("deploy", original)

        logs = self.call(server, "job_logs", job_id=queued["job"])
        lines = [row["line"] for row in logs["lines"]]

        self.assertIn("$ sam deploy", lines)
        self.assertTrue(logs["finished"])
        self.assertEqual(
            self.call(server, "job_logs", job_id=queued["job"], after=logs["next"])[
                "lines"
            ],
            [],
        )
        self.assertEqual(
            self.call(server, "job_status", job_id=queued["job"])["status"], "done"
        )

    def test_a_job_of_another_organization_is_not_found(self):
        server = self.server()

        self.assertIn("no such job", self.refused(server, "job_status", job_id="nope"))


class CiToolsTest(AppToolsCase):
    def test_connect_an_existing_jenkins_job_and_run_it(self):
        from unittest import mock

        from action_platform.core.context import Run, RunRef

        self.setenv("ACME_JENKINS_TOKEN", "tok")
        server = self.server()

        host = self.call(
            server,
            "add_ci_host",
            base_url="https://ci.acme.io/",
            token_env="ACME_JENKINS_TOKEN",
            username="ada",
        )
        self.assertEqual(
            (host["kind"], host["base_url"]), ("jenkins", "https://ci.acme.io")
        )
        self.assertEqual(
            [h["id"] for h in self.call(server, "list_ci_hosts")], [host["id"]]
        )

        with mock.patch(
            "tests.support.ServerRunner.test",
            return_value=None,
        ):
            self.assertEqual(
                self.call(server, "test_ci_host", id=host["id"]),
                {"ok": True, "error": None},
            )

        link = self.call(
            server,
            "set_app_ci",
            id=self.registry_id,
            ci_host=host["id"],
            job="team/app",
        )
        self.assertEqual(
            link, {"kind": "jenkins", "ci_host_id": host["id"], "job": "team/app"}
        )

        with (
            mock.patch(
                "tests.support.ServerRunner.start",
                return_value=RunRef(
                    id="8", url="https://ci.acme.io/job/team/job/app/8/"
                ),
            ) as start,
            mock.patch(
                "tests.support.ServerRunner.runs",
                return_value=[Run(number=8, status="running", branch="main")],
            ),
        ):
            started = self.call(server, "run_ci", id=self.registry_id, ref="main")
            synced = self.call(server, "get_app_ci", id=self.registry_id, sync=True)

        self.assertEqual(started["id"], "8")
        self.assertEqual(start.call_args.args[1], "main")
        self.assertEqual([r["number"] for r in synced["runs"]], [8])
        self.assertEqual(
            self.call(server, "get_app_ci", id=self.registry_id)["link"]["job"],
            "team/app",
        )

    def test_ci_changes_follow_the_role_and_the_scope(self):
        self.setenv("ACME_JENKINS_TOKEN", "tok")
        server = self.server("read,write,release")

        self.assertIn(
            "org.manage",
            self.refused(
                server,
                "add_ci_host",
                base_url="https://ci.acme.io",
                token_env="ACME_JENKINS_TOKEN",
            ),
        )

        reader = self.server("read")
        self.assertIn(
            "app.configure",
            self.refused(reader, "set_app_ci", id=self.registry_id, job="x"),
        )
        self.assertIn(
            "app.flow", self.refused(reader, "run_ci", id=self.registry_id, ref="main")
        )


class HostToolsTest(AppToolsCase):
    def setUp(self):
        super().setUp()
        from app.core.auth.crypto import Sealer
        from app.core.db.models import SourceHost

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

    def test_list_hosts_and_point_an_app_at_one(self):
        server = self.server()

        (row,) = self.call(server, "list_hosts")
        self.assertEqual((row["id"], row["kind"]), ("h1", "github"))
        self.assertNotIn("token", row)
        self.assertEqual(
            self.call(server, "set_app_host", id=self.registry_id, host="h1"),
            {"source_host_id": "h1"},
        )
        self.assertIn(
            "host not found",
            self.refused(server, "set_app_host", id=self.registry_id, host="nope"),
        )

    def test_a_read_only_token_cannot_point_an_app_elsewhere(self):
        self.assertIn(
            "app.flow",
            self.refused(
                self.server("read"), "set_app_host", id=self.registry_id, host="h1"
            ),
        )


class ImportToolsTest(RemoteToolsCase):
    def setUp(self):
        super().setUp()
        from app.core.auth.crypto import Sealer
        from app.core.db.models import SourceHost
        from app.services.projects.organization_import import client, context

        from tests.test_import_github import FakeGithub

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
            def path(self):
                return "acme/web" if self.value == url else None

        self.patch(context, "GitUrl", KnownUrl)

    def test_preview_then_import_and_follow_the_job(self):
        from app.services.jobs.worker import Worker

        server = self.server()

        self.assertEqual(
            [
                o["login"]
                for o in self.call(server, "list_import_organizations", host="gh")[
                    "organizations"
                ]
            ],
            ["ana", "acme"],
        )
        preview = self.call(
            server, "preview_organization_import", host="gh", login="acme"
        )
        self.assertEqual(
            {p["login"]: p["status"] for p in preview["people"]},
            {"ana": "member", "bob": "invitable", "ghost": "no_email"},
        )

        queued = self.call(
            server,
            "import_organization",
            host="gh",
            login="acme",
            repositories=["acme/web"],
            teams=["platform"],
            people=["bob"],
        )
        self.assertEqual(
            Worker(self.app.state.db, self.app.state.secrets, "test").run(once=True), 1
        )

        done = self.call(server, "job_status", job_id=queued["job"])
        self.assertEqual(done["status"], "done", done)
        self.assertEqual(done["result"]["projects"], ["web"])
        self.assertEqual(done["result"]["invitations"], ["bob@example.com"])
        self.assertTrue(self.call(server, "job_logs", job_id=queued["job"])["finished"])
        self.assertEqual(
            [i["email"] for i in self.call(server, "list_invitations")],
            ["bob@example.com"],
        )

    def test_import_needs_org_manage_and_an_admin_scope(self):
        server = self.server("read,write,release")

        for tool, args in (
            ("list_import_organizations", {"host": "gh"}),
            ("preview_organization_import", {"host": "gh", "login": "acme"}),
            (
                "import_organization",
                {"host": "gh", "login": "acme", "repositories": []},
            ),
        ):
            with self.subTest(tool=tool):
                self.assertIn("org.manage", self.refused(server, tool, **args))


class LocalHostedToolsTest(AppToolsCase):
    """The local server's tools that reach the platform the CLI is logged in to."""

    def setUp(self):
        super().setUp()
        from app.repositories.configuration.config_store import ConfigStore

        from action_platform.mcp import build
        from action_platform.remote.client import Remote

        ConfigStore(self.app.state.db).set(
            self.registry_id,
            {
                "project": {"name": "demo"},
                "deploy": {
                    "targets": [
                        {
                            "name": "pypi",
                            "kind": "pypi",
                            "run_by": "github_actions",
                            "workflow": "publish.yml",
                            "package": "demo",
                        }
                    ]
                },
            },
        )
        self.scope = FULL
        self.patch(
            Remote,
            "from_credentials",
            classmethod(lambda cls, server=None: cls(SERVER, self.token(self.scope))),
        )
        self.local = build()
        self.checkout = self.tmp_path / "checkout"
        self.checkout.mkdir()
        (self.checkout / "platform.toml").write_text('[project]\nname = "demo"\n')

    def test_record_deployment_finds_the_checkout_on_the_platform(self):
        row = self.call(
            self.local,
            "record_deployment",
            target="pypi",
            version="1.0.0",
            url="https://pypi.org/p/demo",
            project=str(self.checkout),
        )

        self.assertEqual(
            (row["target"], row["version"], row["executor"], row["status"]),
            ("pypi", "1.0.0", "manual", "success"),
        )
        self.assertIn(
            "nope",
            self.refused(
                self.local, "record_deployment", target="pypi", version="1", app="nope"
            ),
        )

    def test_record_deployment_refuses_a_target_the_app_does_not_have(self):
        self.assertIn(
            "nope",
            self.refused(
                self.local,
                "record_deployment",
                target="nope",
                version="1.0.0",
                app="demo",
            ),
        )

    def test_record_deployment_needs_app_release(self):
        self.scope = "read,write"

        self.assertIn(
            "app.release",
            self.refused(
                self.local, "record_deployment", target="pypi", version="1", app="demo"
            ),
        )

    def test_job_logs_reads_the_hosted_job(self):
        from app.services.jobs import JobQueue

        job = JobQueue(self.app.state.db).enqueue(
            "deploy", {}, organization_id=self.org["id"], app_id="a1"
        )

        logs = self.call(self.local, "job_logs", job_id=job.id)

        self.assertEqual((logs["lines"], logs["finished"]), ([], False))
