"""First-run setup: the setup token the first sign-up needs, `action-platform-api setup token`, and the status that says whether setup is open."""

from __future__ import annotations

import re

from app.core.auth.secrets import Secrets, same_setup_token
from tests.test_operators import OperatorCase

TOKEN = Secrets("s3cret").setup_token()


class SetupTokenTest(OperatorCase):
    def first(self, **extra):
        return self.client.post(
            "/api/auth/sign-up",
            json={
                "name": "Ana",
                "email": "ana@example.com",
                "password": "password1",
                **extra,
            },
        )

    def test_the_token_is_derived_from_the_secret_and_typeable(self):
        self.assertRegex(TOKEN, r"^[A-Z2-7]{4}(-[A-Z2-7]{4}){3}$")
        self.assertEqual(Secrets("s3cret").setup_token(), TOKEN)
        self.assertNotEqual(Secrets("another").setup_token(), TOKEN)
        self.assertTrue(
            same_setup_token(f"  {TOKEN.lower().replace('-', ' ')} ", TOKEN)
        )
        self.assertFalse(same_setup_token("", ""))

    def test_the_first_sign_up_needs_the_token(self):
        missing = self.first()
        wrong = self.first(setup_token="AAAA-BBBB-CCCC-DDDD")

        self.assertEqual(missing.status_code, 403)
        self.assertEqual(missing.json()["error"], "setup_token")
        self.assertIn("action-platform-api setup token", missing.json()["detail"])
        self.assertEqual(wrong.status_code, 403)
        self.assertEqual(self.client.get("/api/auth/status").json()["users"], 0)

        ok = self.first(setup_token=TOKEN.lower().replace("-", ""))

        self.assertEqual(ok.status_code, 201, ok.text)

    def test_status_says_open_until_an_account_exists(self):
        self.assertEqual(self.client.get("/api/auth/status").json()["setup"], "open")

        self.first(setup_token=TOKEN)

        self.assertEqual(self.client.get("/api/auth/status").json()["setup"], "closed")

    def test_after_the_first_account_sign_up_follows_the_invitation_rules(self):
        self.first(setup_token=TOKEN)

        again = self.client.post(
            "/api/auth/sign-up",
            json={
                "name": "Bob",
                "email": "bob@example.com",
                "password": "password1",
                "setup_token": TOKEN,
            },
        )

        self.assertEqual(again.status_code, 403)
        self.assertEqual(again.json()["error"], "forbidden")

    def test_ap_setup_token_replaces_the_derived_one(self):
        self.setenv("AP_SETUP_TOKEN", "my-own-setup-token")

        derived = self.first(setup_token=TOKEN)
        chosen = self.first(setup_token="MY-OWN-SETUP-TOKEN")

        self.assertEqual(derived.status_code, 403)
        self.assertEqual(chosen.status_code, 201, chosen.text)

    def test_the_command_prints_the_token_until_setup_is_closed(self):
        out = self.run_cli("setup", "token").output

        self.assertEqual(out.strip(), TOKEN)

        self.first(setup_token=TOKEN)
        closed = self.run_cli("setup", "token", ok=False)

        self.assertIn("setup is closed", str(closed.exception))

    def test_the_api_points_at_the_command_while_nobody_signed_up(self):
        from app.api.app import build

        with self.assertLogs("action_platform.api", "WARNING") as logs:
            build(
                database_url=f"sqlite:///{self.tmp_path / 'auth.db'}",
                auth_secret="s3cret",
            )

        self.assertTrue(
            any("action-platform-api setup token" in line for line in logs.output)
        )
        self.assertFalse(any(re.search(TOKEN, line) for line in logs.output))

    def test_a_claimed_instance_logs_nothing_about_setup(self):
        from app.api.app import build

        self.first(setup_token=TOKEN)

        with self.assertNoLogs("action_platform.api", "WARNING"):
            build(
                database_url=f"sqlite:///{self.tmp_path / 'auth.db'}",
                auth_secret="s3cret",
            )

    def test_without_an_auth_secret_setup_stays_closed(self):
        from fastapi.testclient import TestClient

        from app.api.app import build

        client = TestClient(
            build(
                database_url=f"sqlite:///{self.tmp_path / 'nosecret.db'}",
                auth_secret="",
            )
        )
        res = client.post(
            "/api/auth/sign-up",
            json={
                "name": "Ana",
                "email": "ana@example.com",
                "password": "password1",
                "setup_token": TOKEN,
            },
        )

        self.assertEqual(res.status_code, 503)
        self.assertEqual(client.get("/api/auth/status").json()["setup"], "closed")
