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
            prefer=None,
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

    def test_a_background_deploy_answers_with_its_job(self):
        remote = client.Remote("https://p.example", "tok")
        self.answer = {"job": "j1", "poll": "/api/v1/jobs/j1", "status": "queued"}

        queued = remote.deploy_later("a1", "prod", "1.2.3")

        self.assertEqual(queued.job, "j1")
        self.assertEqual(
            self.seen["body"], {"stage": "prod", "dry_run": False, "version": "1.2.3"}
        )

    def test_a_preflight_answers_inline(self):
        self.answer = [{"target": "api", "ok": True, "version": "1.2.3"}]

        (result,) = client.Remote("https://p.example", "tok").deploy("a1", "prod")

        self.assertEqual((result.target, result.ok), ("api", True))
        self.assertEqual(
            self.seen["body"], {"stage": "prod", "dry_run": True, "version": None}
        )

    def followed(self, *jobs: object) -> list[tuple[str, str]]:
        """Answer the queued call with job j1, then each GET of it with the next of `jobs`; the calls made, in order."""
        calls: list[tuple[str, str]] = []
        states = list(jobs)

        def fake_request(method, url, body=None, token=None, **_):
            calls.append((method, url.removeprefix("https://p.example/api/v1/")))

            if method == "POST":
                return {"job": "j1", "poll": "/api/v1/jobs/j1", "status": "queued"}

            state = states.pop(0)

            if isinstance(state, BaseException):
                raise state

            return {"id": "j1", "kind": "deploy", **state}

        self.patch(client, "_request", fake_request)
        self.patch(client.time, "sleep", lambda s: None)

        return calls

    def test_a_deploy_runs_as_a_job_and_is_followed_until_it_ends(self):
        calls = self.followed(
            {"status": "queued"},
            {"status": "running"},
            {
                "status": "done",
                "result": [
                    {
                        "target": "api",
                        "ok": True,
                        "version": "0.60.0-rc.1",
                        "stage": "dev",
                    }
                ],
            },
        )

        results = client.Remote("https://p.example", "tok").deploy(
            "a1", "dev", dry_run=False, version="0.60.0-rc.1"
        )

        self.assertEqual(
            [(r.target, r.ok, r.version) for r in results],
            [("api", True, "0.60.0-rc.1")],
        )
        self.assertEqual(
            calls,
            [
                ("POST", "apps/a1/deploy"),
                ("GET", "jobs/j1"),
                ("GET", "jobs/j1"),
                ("GET", "jobs/j1"),
            ],
        )

    def test_a_failed_deploy_job_raises_its_error(self):
        self.followed({"status": "failed", "error": "jenkins said no"})

        with self.assertRaisesRegex(ActionPlatformError, "jenkins said no"):
            client.Remote("https://p.example", "tok").deploy(
                "a1", "dev", dry_run=False, version="1.0.0"
            )

    def test_a_poll_that_fails_is_retried(self):
        self.followed(
            client.RemoteError(502, "Bad Gateway"),
            TimeoutError("timed out"),
            {
                "status": "done",
                "result": [{"target": "api", "ok": True, "version": "1.0.0"}],
            },
        )

        (result,) = client.Remote("https://p.example", "tok").deploy(
            "a1", "dev", dry_run=False, version="1.0.0"
        )

        self.assertTrue(result.ok)

    def test_a_job_that_cannot_be_read_by_the_deadline_names_its_id(self):
        self.followed(client.RemoteError(401, "token expired"))

        with self.assertRaisesRegex(ActionPlatformError, "job j1 could not be read"):
            client.Remote("https://p.example", "tok").deploy(
                "a1", "dev", dry_run=False, version="1.0.0", wait=0
            )

    def test_a_deploy_still_running_after_the_wait_answers_with_its_job(self):
        self.followed({"status": "running"})

        queued = client.Remote("https://p.example", "tok").deploy(
            "a1", "dev", dry_run=False, version="1.0.0", wait=0
        )

        self.assertIsInstance(queued, schemas.JobQueued)
        self.assertEqual((queued.job, queued.status), ("j1", "running"))

    def test_a_release_runs_as_a_job_and_answers_its_preview(self):
        calls = self.followed({"status": "done", "result": ANSWER})

        preview = client.Remote("https://p.example", "tok").release(
            "a1", "minor", dry_run=False
        )

        self.assertEqual((preview.next, preview.dry_run), ("1.1.0", False))
        self.assertEqual(calls[0], ("POST", "apps/a1/release"))

    def test_a_sync_runs_as_a_job_and_answers_the_entry(self):
        calls = self.followed(
            {
                "status": "done",
                "result": {
                    "id": "a1",
                    "name": "demo",
                    "url": "https://x/demo.git",
                    "path": "/w/a1",
                },
            }
        )

        entry = client.Remote("https://p.example", "tok").sync_app("a1")

        self.assertEqual(entry.id, "a1")
        self.assertEqual(calls, [("POST", "apps/a1/sync"), ("GET", "jobs/j1")])

    def test_calls_v1_with_bearer(self):
        remote = client.Remote("https://p.example", "tok")

        remote.release("p1", "minor")
        self.assertEqual(self.seen["method"], "POST")
        self.assertEqual(self.seen["url"], "https://p.example/api/v1/apps/p1/release")
        self.assertEqual(
            self.seen["body"], {"level": "minor", "dry_run": True, "branch": None}
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

    def test_access_calls_reach_the_access_routes(self):
        remote = client.Remote("https://p.example", "tok")
        self.answer = {"organization_members": 2, "services": []}

        audit = remote.access_audit("github", organization="acme")

        self.assertEqual(audit.organization_members, 2)
        self.assertEqual(
            self.seen["url"], "https://p.example/api/v1/access/audit?service=github"
        )
        self.assertEqual(self.seen["organization"], "acme")

        self.answer = {"dry_run": True}

        for call, path, body in (
            (
                lambda: remote.access_grant("ana@x.dev", "github", "repo/api", "push"),
                "grant",
                {
                    "person": "ana@x.dev",
                    "service": "github",
                    "resource": "repo/api",
                    "level": "push",
                    "account": None,
                    "apply": False,
                },
            ),
            (
                lambda: remote.access_revoke("ana@x.dev", "github", "repo/api"),
                "revoke",
                {
                    "person": "ana@x.dev",
                    "service": "github",
                    "resource": "repo/api",
                    "apply": False,
                },
            ),
            (
                lambda: remote.access_offboard("ana@x.dev", apply=True),
                "offboard",
                {
                    "person": "ana@x.dev",
                    "apply": True,
                    "remove_from_platform": False,
                },
            ),
            (
                lambda: remote.access_sync(links={"a@x.dev": {"github": "a"}}),
                "sync",
                {
                    "service": None,
                    "apply": False,
                    "reimport": False,
                    "links": {"a@x.dev": {"github": "a"}},
                },
            ),
        ):
            with self.subTest(path=path):
                self.assertTrue(call().dry_run)
                self.assertEqual(self.seen["method"], "POST")
                self.assertEqual(
                    self.seen["url"], f"https://p.example/api/v1/access/{path}"
                )
                self.assertEqual(self.seen["body"], body)

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

        self.assertIsInstance(remote.release("p1", "minor"), schemas.ReleasePreview)

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

    def test_me_names_the_role_by_its_label_first(self):
        self.assertEqual(
            schemas.Me(role="admin", role_label="Admin").role_name, "Admin"
        )
        self.assertEqual(schemas.Me(role="admin").role_name, "admin")
        self.assertIsNone(schemas.Me().role_name)

    def test_an_answer_missing_a_guaranteed_field_is_refused(self):
        remote = client.Remote("https://p.example", "tok")
        self.answer = {"next": "1.1.0"}

        with self.assertRaises(ValidationError):
            remote.release("p1")

    def test_from_credentials_requires_login(self):
        with self.assertRaisesRegex(ActionPlatformError, "login"):
            client.Remote.from_credentials()


JWT = "aaaa.bbbb.cccc"


class LoginWithTokenTest(LoginCase):
    def test_keeps_the_token_once_the_platform_accepts_it(self):
        self.answers()
        self.patch(
            client,
            "_request",
            lambda method, url, body=None, token=None, **kw: (
                self.calls.append((method, url, token))
                or {"user": {"email": "me@example.com"}, "scope": ["read", "write"]}
            ),
        )

        creds, who = client.login_with_token("https://p.example/", f" {JWT}\n")

        self.assertEqual(
            creds, credentials.Credentials("https://p.example", JWT, "read write")
        )
        self.assertEqual(credentials.load(), creds)
        self.assertEqual(who.user["email"], "me@example.com")
        self.assertEqual(self.calls, [("GET", "https://p.example/api/v1/me", JWT)])
        self.assertEqual(self.opened, [])

    def test_a_refused_or_malformed_token_is_not_saved(self):
        def refuse(*args, **kwargs):
            raise client.RemoteError(401, "unauthorized")

        self.patch(client, "_request", refuse)

        with self.assertRaisesRegex(ActionPlatformError, "invalid, expired or revoked"):
            client.login_with_token("https://p.example", JWT)

        with self.assertRaisesRegex(ActionPlatformError, "not an API token"):
            client.login_with_token("https://p.example", "session-token")

        self.assertIsNone(credentials.load())
