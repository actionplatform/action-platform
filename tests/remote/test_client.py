"""action_platform.remote.client — the device-flow login and the HTTP client, without network."""

from __future__ import annotations

import json

from pydantic import ValidationError

from action_platform.core.exception import ActionPlatformError
from action_platform.remote import client, credentials, schemas
from tests.support import TempCase

DEVICE_CODE = {
    "device_code": "dc",
    "user_code": "ABCD-EFGH",
    "verification_uri": "/device",
    "interval": 0,
    "expires_in": 60,
}


class LoginCase(TempCase):
    def setUp(self):
        super().setUp()
        self.setenv("AP_HOME", str(self.tmp_path))
        self.delenv("AP_SERVER")
        self.delenv("AP_TOKEN")
        self.calls: list[tuple[str, str]] = []
        self.patch(client.time, "sleep", lambda s: None)
        self.opened: list[str] = []
        self.patch(client.webbrowser, "open", lambda u: self.opened.append(u))

    def answers(self, *replies) -> None:
        it = iter([DEVICE_CODE, *replies])

        def fake_request(
            method,
            url,
            body=None,
            token=None,
            timeout=60,
            client=None,
            organization=None,
        ):
            self.calls.append((method, url))
            answer = next(it)
            if isinstance(answer, Exception):
                raise answer
            return answer

        self.patch(client, "_request", fake_request)


class LoginTest(LoginCase):
    def test_polls_until_approved_and_survives_a_network_blip(self):
        self.answers(
            client.RemoteError(
                400, "Authorization pending", code="authorization_pending"
            ),
            client.RemoteError(400, "slow_down"),
            ActionPlatformError("cannot reach https://p.example: timed out"),
            {
                "access_token": "session-token",
                "token_type": "Bearer",
                "scope": "read write",
            },
            {"token": "jwt-token", "scope": "read write"},
        )
        shown: list[str] = []

        creds = client.login(
            "https://p.example/", echo=shown.append, scope="read,write"
        )

        self.assertEqual(
            creds,
            credentials.Credentials("https://p.example", "jwt-token", "read write"),
        )
        self.assertEqual(credentials.load(), creds)
        self.assertEqual(self.opened, ["https://p.example/device"])
        self.assertTrue(any("ABCD-EFGH" in line for line in shown))
        self.assertEqual(
            self.calls[0], ("POST", "https://p.example/api/auth/device/code")
        )
        self.assertEqual(self.calls[-1], ("POST", "https://p.example/api/v1/tokens"))
        self.assertEqual(len(self.calls), 6)

    def test_scope_is_validated_before_anything_is_sent(self):
        self.answers()

        with self.assertRaisesRegex(ActionPlatformError, "unknown scope"):
            client.login("https://p.example", echo=lambda s: None, scope="read,root")

        self.assertEqual(self.calls, [])
        self.assertEqual(client.parse_scope("write"), ["read", "write"])
        self.assertEqual(
            client.parse_scope("admin, read release"), ["read", "release", "admin"]
        )

    def test_denied_expired_and_unknown_errors(self):
        self.answers(client.RemoteError(400, "access_denied"))
        with self.assertRaisesRegex(ActionPlatformError, "denied"):
            client.login("https://p.example", echo=lambda s: None)

        self.answers(client.RemoteError(400, "expired_token"))
        with self.assertRaisesRegex(ActionPlatformError, "expired"):
            client.login("https://p.example", echo=lambda s: None)

        self.answers(client.RemoteError(400, "request pending review"))
        with self.assertRaises(client.RemoteError):
            client.login("https://p.example", echo=lambda s: None)

    def test_reads_the_oauth_error_code_from_the_body(self):
        import io
        import urllib.error

        body = json.dumps(
            {
                "error": "authorization_pending",
                "error_description": "Authorization pending",
            }
        ).encode()
        err = urllib.error.HTTPError("u", 400, "Bad Request", {}, io.BytesIO(body))
        self.patch(
            client.urllib.request,
            "urlopen",
            lambda *a, **k: (_ for _ in ()).throw(err),
        )

        with self.assertRaises(client.RemoteError) as caught:
            client._request("POST", "https://p.example/x", {})

        self.assertEqual(caught.exception.code, "authorization_pending")
        self.assertEqual(caught.exception.detail, "Authorization pending")

    def test_gives_up_after_repeated_network_failures(self):
        self.answers(*[ActionPlatformError("cannot reach") for _ in range(7)])

        with self.assertRaisesRegex(ActionPlatformError, "giving up"):
            client.login("https://p.example", echo=lambda s: None)


LISTED = ("apps", "projects", "teams", "members", "commits")
ANSWER = {
    "ok": True,
    "id": "p1",
    "name": "Shop",
    "slug": "shop",
    "registry_id": "r1",
    "current": "1.0.0",
    "next": "1.1.0",
    "changelog": "",
    "dry_run": False,
}


class RemoteClientTest(TempCase):
    def setUp(self):
        super().setUp()
        self.setenv("AP_HOME", str(self.tmp_path))
        self.delenv("AP_SERVER")
        self.delenv("AP_TOKEN")
        self.seen: dict = {}
        self.rows: list = []
        self.answer: object = ANSWER

        def fake_request(
            method,
            url,
            body=None,
            token=None,
            timeout=60,
            client=None,
            organization=None,
        ):
            self.seen.update(
                method=method,
                url=url,
                body=body,
                token=token,
                client=client,
                organization=organization,
            )
            path = url.split("?")[0]

            if method == "GET" and path.endswith(LISTED):
                return self.rows

            return self.answer

        self.patch(client, "_request", fake_request)

    def test_calls_v1_with_bearer(self):
        remote = client.Remote("https://p.example", "tok")

        remote.release("p1", "minor", dry_run=False)
        self.assertEqual(self.seen["method"], "POST")
        self.assertEqual(self.seen["url"], "https://p.example/api/v1/apps/p1/release")
        self.assertEqual(
            self.seen["body"], {"level": "minor", "dry_run": False, "branch": None}
        )
        self.assertEqual(self.seen["token"], "tok")
        self.assertEqual(self.seen["client"], "action-platform-cli")

        remote.client = "claude-code/2.1"
        remote.apps()
        self.assertEqual(self.seen["client"], "claude-code/2.1")

        remote.commits("p1", limit=5)
        self.assertEqual(
            self.seen["url"], "https://p.example/api/v1/apps/p1/commits?limit=5"
        )

        remote.write_manifest("p1", "[project]\n")
        self.assertEqual(self.seen["method"], "PUT")

    def test_organization_level_calls_send_the_organization(self):
        remote = client.Remote("https://p.example", "tok")

        for call in (
            lambda: remote.projects(organization="acme"),
            lambda: remote.teams(organization="acme"),
            lambda: remote.members(organization="acme"),
            lambda: remote.create_project("Shop", "", organization="acme"),
            lambda: remote.create_team("Core", "", organization="acme"),
            lambda: remote.add_team_member("t1", "u1", organization="acme"),
            lambda: remote.assign_project_team("p1", None, organization="acme"),
            lambda: remote.set_member_role("u1", "viewer", organization="acme"),
            lambda: remote.add_app("p1", "https://x/y.git", None, "acme"),
            lambda: remote.remove_app("p1", "d1", True, "acme"),
            lambda: remote.delete_project("p1", False, "acme"),
        ):
            with self.subTest(call=call):
                call()
                self.assertEqual(self.seen["organization"], "acme")

        remote.remove_app("p1", "d1", True, "acme")
        self.assertEqual(
            self.seen["url"],
            "https://p.example/api/v1/projects/p1/apps/d1?repository=true",
        )
        self.assertIsNone(self.seen["body"])

        remote.projects()
        self.assertIsNone(self.seen["organization"])

    def test_answers_come_back_as_the_schemas(self):
        remote = client.Remote("https://p.example", "tok")
        self.rows = [
            {
                "id": "p1",
                "name": "Shop",
                "slug": "shop",
                "apps": [{"id": "d1", "name": "orders", "registry_id": "r1"}],
                "organization": {"id": "o1", "name": "Acme"},
                "tearing_down": False,
            }
        ]

        (project,) = remote.projects()

        self.assertIsInstance(project, schemas.ProjectRow)
        self.assertEqual(project.apps[0].registry_id, "r1")
        self.assertEqual(project.organization.id, "o1")
        self.assertIs(project.model_extra["tearing_down"], False)

        self.assertIsInstance(
            remote.release("p1", "minor", dry_run=False), schemas.ReleasePreview
        )

        self.answer = {
            "user": {"email": "me@example.com"},
            "permissions": {"app.release": True},
        }
        who = remote.whoami()

        self.assertIsInstance(who, schemas.Me)
        self.assertEqual(who.user["email"], "me@example.com")
        self.assertIsNone(who.organization)

        self.answer = None
        self.assertEqual(remote.whoami().permissions, {})

    def test_an_answer_missing_a_guaranteed_field_is_refused(self):
        remote = client.Remote("https://p.example", "tok")
        self.answer = {"next": "1.1.0"}

        with self.assertRaises(ValidationError):
            remote.release("p1")

    def test_from_credentials_requires_login(self):
        with self.assertRaisesRegex(ActionPlatformError, "login"):
            client.Remote.from_credentials()
