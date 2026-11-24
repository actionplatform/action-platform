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

        self.patch(client.urllib.request, "urlopen", urlopen)

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
            return result.structured_content.get("result", result.structured_content)

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
