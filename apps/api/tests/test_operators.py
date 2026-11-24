"""`action-platform-api users` and `tokens`: operator commands against the API's database, and a disabled account kept out everywhere."""

from __future__ import annotations

import importlib
from urllib.parse import parse_qs, urlparse

from tests.test_auth import AuthCase


class OperatorCase(AuthCase):
    def setUp(self):
        super().setUp()
        from typer.testing import CliRunner

        self.cli = importlib.import_module("app.cli.app")
        self.runner = CliRunner()
        self.setenv("AP_DATABASE_URL", f"sqlite:///{self.tmp_path / 'auth.db'}")
        self.setenv("AP_AUTH_SECRET", "s3cret")
        self.setenv("AP_PUBLIC_URL", "https://ap.example.com/")

    def run_cli(self, *args, input=None, ok=True):
        result = self.runner.invoke(self.cli.app, list(args), input=input)

        if ok:
            self.assertEqual(result.exit_code, 0, result.output)

        return result

    def sign_in(self, email="ana@example.com", password="password1"):
        return self.client.post(
            "/api/auth/sign-in", json={"email": email, "password": password}
        )

    def mint(self, session: str) -> str:
        res = self.client.post(
            "/api/v1/tokens",
            json={"scope": "read write", "name": "cli"},
            headers={"Authorization": f"Bearer {session}"},
        )
        self.assertEqual(res.status_code, 200, res.text)

        return res.json()["token"]

    def me(self, token: str):
        return self.client.get(
            "/api/v1/me", headers={"Authorization": f"Bearer {token}"}
        )

    def session_alive(self, session: str) -> bool:
        return (
            self.client.get("/api/auth/session", headers=self.h(session)).status_code
            == 200
        )

    @staticmethod
    def link_token(output: str) -> str:
        line = next(line for line in output.splitlines() if "/reset-password?" in line)
        link = urlparse(line.strip())
        assert f"{link.scheme}://{link.netloc}{link.path}" == (
            "https://ap.example.com/reset-password"
        ), line

        return parse_qs(link.query)["token"][0]


class UsersTest(OperatorCase):
    def test_list_shows_status_and_memberships(self):
        self.owner()

        out = self.run_cli("users", "list").output

        self.assertIn("ana@example.com\tAna\tactive", out)
        self.assertIn("acme:owner", out)

    def test_create_with_a_password_from_stdin_joins_the_organization(self):
        self.owner()

        out = self.run_cli(
            "users",
            "create",
            "Bob@Example.com",
            "--name",
            "Bob",
            "--org",
            "acme",
            "--role",
            "viewer",
            "--password-stdin",
            input="bob-password\n",
        ).output

        self.assertIn("created bob@example.com in acme as viewer", out)
        self.assertNotIn("bob-password", out)
        self.assertNotIn("reset-password", out)
        signed = self.sign_in("bob@example.com", "bob-password")
        self.assertEqual(signed.status_code, 200, signed.text)
        who = self.client.get(
            "/api/auth/session", headers=self.h(signed.json()["session"]["token"])
        ).json()
        self.assertEqual(who["role"], "viewer")

    def test_create_without_a_password_prints_a_set_password_link(self):
        self.owner()

        out = self.run_cli("users", "create", "bob@example.com", "--name", "Bob").output
        reset = self.client.post(
            "/api/auth/password/reset",
            json={"token": self.link_token(out), "password": "chosen-by-bob"},
        )

        self.assertIn("valid 24 hours", out)
        self.assertEqual(reset.status_code, 204, reset.text)
        self.assertEqual(
            self.sign_in("bob@example.com", "chosen-by-bob").status_code, 200
        )

    def test_create_refuses_a_duplicate_and_a_weak_password(self):
        self.owner()

        duplicate = self.run_cli(
            "users", "create", "ana@example.com", "--name", "Ana", ok=False
        )
        weak = self.run_cli(
            "users",
            "create",
            "bob@example.com",
            "--name",
            "Bob",
            "--password-stdin",
            input="short\n",
            ok=False,
        )

        self.assertIn("already exists", str(duplicate.exception))
        self.assertIn("at least 8", str(weak.exception))

    def test_reset_password_from_stdin_ends_sessions_and_revokes_tokens(self):
        session = self.owner()["token"]
        token = self.mint(session)

        out = self.run_cli(
            "users",
            "reset-password",
            "ana@example.com",
            "--password-stdin",
            input="brand-new-pass\n",
        ).output

        self.assertIn("1 API token(s) revoked", out)
        self.assertIn(
            "the CLI and MCP signed in as this user have to log in again", out
        )
        self.assertFalse(self.session_alive(session))
        self.assertEqual(self.me(token).status_code, 401)
        self.assertEqual(self.sign_in(password="password1").status_code, 401)
        self.assertEqual(self.sign_in(password="brand-new-pass").status_code, 200)

    def test_reset_password_link_retires_the_old_password_at_once(self):
        session = self.owner()["token"]

        out = self.run_cli("users", "reset-password", "ana@example.com").output

        self.assertFalse(self.session_alive(session))
        self.assertEqual(self.sign_in(password="password1").status_code, 401)
        reset = self.client.post(
            "/api/auth/password/reset",
            json={"token": self.link_token(out), "password": "from-the-link"},
        )
        self.assertEqual(reset.status_code, 204, reset.text)
        self.assertEqual(self.sign_in(password="from-the-link").status_code, 200)

    def test_a_link_needs_the_public_url_and_changes_nothing_without_it(self):
        self.owner()
        self.setenv("AP_PUBLIC_URL", "")

        result = self.run_cli("users", "reset-password", "ana@example.com", ok=False)

        self.assertIn("AP_PUBLIC_URL", str(result.exception))
        self.assertEqual(self.sign_in().status_code, 200)

    def test_unknown_email(self):
        result = self.run_cli("users", "disable", "nobody@example.com", ok=False)

        self.assertIn("no user with the email", str(result.exception))

    def test_disable_blocks_sign_in_sessions_and_tokens_until_enabled(self):
        session = self.owner()["token"]
        token = self.mint(session)

        out = self.run_cli("users", "disable", "ana@example.com").output

        self.assertIn("1 session(s) ended", out)
        self.assertFalse(self.session_alive(session))
        refused = self.sign_in()
        self.assertEqual(refused.status_code, 403)
        self.assertEqual(refused.json()["error"], "disabled")
        self.assertEqual(self.me(token).status_code, 401)
        self.assertEqual(
            self.client.post(
                "/api/auth/tokens/verify", json={"token": token}
            ).status_code,
            401,
        )
        self.assertIn("\tdisabled\t", self.run_cli("users", "list").output)

        self.run_cli("users", "enable", "ana@example.com")

        self.assertEqual(self.sign_in().status_code, 200)
        self.assertEqual(self.me(token).status_code, 200)

    def test_a_disabled_account_cannot_finish_the_device_flow(self):
        from app.core.db.models import User

        session = self.owner()["token"]
        code = self.client.post("/api/auth/device/code", json={}).json()
        self.client.post(
            "/api/auth/device/approve",
            json={"user_code": code["user_code"]},
            headers=self.h(session),
        )
        with self.app.state.db.session() as db:
            user = db.query(User).one()
            user.disabled_at = user.created_at

        res = self.client.post(
            "/api/auth/device/token",
            json={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": code["device_code"],
            },
        )

        self.assertEqual(res.status_code, 403, res.text)

    def test_commands_need_the_database_and_the_secret(self):
        self.setenv("AP_AUTH_SECRET", "")
        self.setenv("BETTER_AUTH_SECRET", "")

        result = self.run_cli("users", "list", ok=False)

        self.assertIn("AP_AUTH_SECRET", str(result.exception))


class RecoveryRevokesTokensTest(OperatorCase):
    def test_a_reset_link_from_email_also_signs_out_the_cli_and_mcp(self):
        session = self.owner()["token"]
        token = self.mint(session)

        with self.app.state.db.session() as db:
            from app.services.auth.service import AuthService

            auth = AuthService(db, self.app.state.secrets)
            _, raw = auth.request_password_reset("ana@example.com")

        self.client.post(
            "/api/auth/password/reset", json={"token": raw, "password": "new-password1"}
        )

        self.assertEqual(self.me(token).status_code, 401)


class TokensTest(OperatorCase):
    def test_issue_prints_only_the_token_on_stdout_and_it_works(self):
        self.owner()

        result = self.runner.invoke(
            self.cli.app,
            [
                "tokens",
                "issue",
                "ana@example.com",
                "--scope",
                "read,write",
                "--org",
                "acme",
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        raw = result.stdout.strip().splitlines()[-1]
        self.assertEqual(len(raw.split(".")), 3)
        self.assertIn("read write on acme", result.output)
        me = self.me(raw)
        self.assertEqual(me.status_code, 200, me.text)
        self.assertEqual(me.json()["scope"], ["read", "write"])
        self.assertEqual(me.json()["organization"]["slug"], "acme")

    def test_scope_is_narrowed_to_the_role_and_days_shorten_the_lifetime(self):
        self.owner()
        self.run_cli(
            "users",
            "create",
            "viewer@example.com",
            "--name",
            "Vi",
            "--org",
            "acme",
            "--role",
            "viewer",
            "--password-stdin",
            input="viewer-pass\n",
        )

        result = self.runner.invoke(
            self.cli.app,
            [
                "tokens",
                "issue",
                "viewer@example.com",
                "--scope",
                "read,write,admin",
                "--days",
                "7",
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn(
            "token for viewer@example.com: read on all organizations", result.output
        )
        me = self.me(result.stdout.strip().splitlines()[-1]).json()
        self.assertEqual(me["scope"], ["read"])

    def test_refusals(self):
        self.owner()

        no_scope = self.run_cli(
            "tokens", "issue", "ana@example.com", "--scope", "nope", ok=False
        )
        app_alone = self.run_cli(
            "tokens", "issue", "ana@example.com", "--app", "a1", ok=False
        )
        no_org = self.run_cli(
            "tokens", "issue", "ana@example.com", "--org", "ghost", ok=False
        )

        self.assertIn("--scope", str(no_scope.exception))
        self.assertIn("--project", str(app_alone.exception))
        self.assertIn("no organization ghost", str(no_org.exception))
