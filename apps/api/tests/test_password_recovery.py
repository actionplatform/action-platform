"""Password recovery: the forgot and reset routes, the emailed link, single use, expiry and sessions closed."""

from __future__ import annotations

from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from action_platform.core.exception import ProviderError

from tests.test_auth import AuthCase


class Outbox:
    def __init__(self) -> None:
        self.sent = []
        self.fail = False

    def send(self, mail) -> None:
        if self.fail:
            raise ProviderError("smtp down")

        self.sent.append(mail)


class PasswordRecoveryTest(AuthCase):
    def setUp(self):
        super().setUp()
        self.outbox = Outbox()
        self.app.state.mailer = self.outbox

    def forgot(self, email="ana@example.com"):
        return self.client.post("/api/auth/password/forgot", json={"email": email})

    def reset(self, token, password="new-password1"):
        return self.client.post(
            "/api/auth/password/reset", json={"token": token, "password": password}
        )

    def token(self) -> str:
        link = urlparse(self.outbox.sent[-1].text.split("\n\n")[2])
        self.assertEqual(
            f"{link.scheme}://{link.netloc}{link.path}",
            "https://ap.example.com/reset-password",
        )

        return parse_qs(link.query)["token"][0]

    def sign_in(self, password):
        return self.client.post(
            "/api/auth/sign-in", json={"email": "ana@example.com", "password": password}
        )

    def test_status_says_recovery_is_available(self):
        self.assertTrue(self.client.get("/api/auth/status").json()["password_recovery"])
        self.app.state.mailer = None
        self.assertFalse(
            self.client.get("/api/auth/status").json()["password_recovery"]
        )

    def test_reset_sets_the_new_password_and_closes_every_session(self):
        old = self.sign_up().json()["session"]["token"]

        self.assertEqual(self.forgot("  ANA@example.com ").status_code, 202)
        self.assertEqual(len(self.outbox.sent), 1)
        self.assertEqual(self.outbox.sent[0].to, "ana@example.com")
        self.assertEqual(self.reset(self.token()).status_code, 204)

        self.assertEqual(
            self.client.get("/api/auth/session", headers=self.h(old)).status_code, 401
        )
        self.assertEqual(self.sign_in("password1").status_code, 401)
        self.assertEqual(self.sign_in("new-password1").status_code, 200)

    def test_a_link_works_once(self):
        self.sign_up()
        self.forgot()
        token = self.token()

        self.assertEqual(self.reset(token).status_code, 204)
        refused = self.reset(token, "another-password1")
        self.assertEqual(refused.status_code, 400)
        self.assertEqual(refused.json()["error"], "invalid_token")

    def test_a_new_request_replaces_the_previous_link(self):
        self.sign_up()
        self.forgot()
        first = self.token()
        self.forgot()
        second = self.token()

        self.assertEqual(self.reset(first).status_code, 400)
        self.assertEqual(self.reset(second).status_code, 204)

    def test_an_expired_link_is_refused(self):
        from app.core.db.models import Verification

        self.sign_up()
        self.forgot()
        token = self.token()

        with self.app.state.db.session() as db:
            for row in db.query(Verification).all():
                row.expires_at = row.expires_at - timedelta(hours=1)

        self.assertEqual(self.reset(token).status_code, 400)

    def test_a_weak_password_keeps_the_link(self):
        self.sign_up()
        self.forgot()
        token = self.token()

        weak = self.reset(token, "short")
        self.assertEqual(weak.status_code, 400)
        self.assertEqual(weak.json()["error"], "weak_password")
        self.assertEqual(self.reset(token).status_code, 204)

    def test_an_unknown_email_answers_the_same_and_sends_nothing(self):
        self.sign_up()

        self.assertEqual(self.forgot("nobody@example.com").status_code, 202)
        self.assertEqual(self.outbox.sent, [])

    def test_a_made_up_token_is_refused(self):
        self.sign_up()

        self.assertEqual(self.reset("not-a-token").status_code, 400)

    def test_a_failing_mail_server_still_answers_202(self):
        self.sign_up()
        self.outbox.fail = True

        self.assertEqual(self.forgot().status_code, 202)

    def test_without_smtp_the_route_says_so(self):
        self.app.state.mailer = None

        self.assertEqual(self.forgot().status_code, 503)

    def test_the_link_is_stored_as_a_hash(self):
        from app.core.db.models import Verification

        self.sign_up()
        self.forgot()
        token = self.token()

        with self.app.state.db.session() as db:
            values = [row.value for row in db.query(Verification).all()]

        self.assertEqual(len(values), 1)
        self.assertNotEqual(values[0], token)
        self.assertNotIn(token, values[0])

    def test_forgot_is_rate_limited(self):
        self.sign_up()
        codes = [self.forgot().status_code for _ in range(6)]

        self.assertEqual(codes[:5], [202] * 5)
        self.assertEqual(codes[5], 429)
