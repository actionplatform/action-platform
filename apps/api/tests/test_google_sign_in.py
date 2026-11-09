"""Sign in with Google: start and callback routes, PKCE and signed state, linking by subject or verified email, sign-up only by invitation."""

from __future__ import annotations

import base64
import hashlib
import json
import time
from unittest import mock
from urllib.parse import parse_qs, urlparse

from action_platform.core.exception import ProviderError

from tests.test_auth import AuthCase

ORIGIN = "https://ap.example.com"


def id_token(**claims) -> str:
    body = {
        "iss": "https://accounts.google.com",
        "aud": "cid",
        "sub": "google-1",
        "email": "ana@example.com",
        "email_verified": True,
        "name": "Ana Google",
        "picture": "https://lh3.example/ana.png",
        "exp": int(time.time()) + 600,
        **claims,
    }

    def part(data) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    return f"{part({'alg': 'RS256'})}.{part(body)}.signature"


class GoogleCase(AuthCase):
    def setUp(self):
        super().setUp()
        from app.services.auth.google import GoogleConfig

        self.app.state.google = GoogleConfig("cid", "csecret")
        self.exchanged = []
        self.token = id_token()
        patcher = mock.patch(
            "app.services.auth.google.http.post_form", side_effect=self.post_form
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def post_form(self, url, form, headers=None):
        self.exchanged.append((url, form))

        return {"access_token": "at", "id_token": self.token}

    def start(self, next_path="/projects"):
        res = self.client.post(
            "/api/auth/google/start", json={"origin": ORIGIN, "next": next_path}
        )
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        query = parse_qs(urlparse(body["url"]).query)

        return body["verifier"], query

    def google(self, next_path="/projects", **override):
        verifier, query = self.start(next_path)
        payload = {
            "origin": ORIGIN,
            "code": "the-code",
            "state": query["state"][0],
            "verifier": verifier,
            **override,
        }

        return self.client.post("/api/auth/google/callback", json=payload)

    def invite(self, email="bia@example.com") -> str:
        from datetime import timedelta

        from app.core.db.models import Invitation
        from app.core.shared.clock import now

        owner = self.owner()

        with self.app.state.db.session() as db:
            db.add(
                Invitation(
                    id="inv-1",
                    organization_id=owner["org"]["id"],
                    email=email,
                    role="member",
                    status="pending",
                    expires_at=now() + timedelta(days=1),
                    inviter_id=owner["user"]["id"],
                )
            )

        return "inv-1"


class GoogleStartTest(GoogleCase):
    def test_status_says_google_is_available(self):
        self.assertTrue(self.client.get("/api/auth/status").json()["google"])
        self.app.state.google = None
        self.assertFalse(self.client.get("/api/auth/status").json()["google"])

    def test_start_sends_the_browser_to_google_with_pkce(self):
        verifier, query = self.start()

        self.assertEqual(query["client_id"], ["cid"])
        self.assertEqual(
            query["redirect_uri"], [f"{ORIGIN}/api/sign-in/google/callback"]
        )
        self.assertEqual(query["scope"], ["openid email profile"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        self.assertEqual(query["code_challenge"], [challenge])

    def test_not_configured_is_404(self):
        self.app.state.google = None
        res = self.client.post("/api/auth/google/start", json={"origin": ORIGIN})

        self.assertEqual(res.status_code, 404)


class GoogleCallbackTest(GoogleCase):
    def test_existing_user_signs_in_and_gets_linked(self):
        self.sign_up()
        res = self.google("/projects/acme")

        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["user"]["email"], "ana@example.com")
        self.assertEqual(res.json()["next"], "/projects/acme")
        url, form = self.exchanged[-1]
        self.assertEqual(url, "https://oauth2.googleapis.com/token")
        self.assertEqual(form["code"], "the-code")
        self.assertEqual(form["grant_type"], "authorization_code")
        self.assertTrue(form["code_verifier"])

        from app.core.db.models import Account

        with self.app.state.db.session() as db:
            linked = db.query(Account).filter_by(provider_id="google").all()
        self.assertEqual([a.account_id for a in linked], ["google-1"])

    def test_linked_account_signs_in_by_subject_after_email_changes(self):
        self.sign_up()
        self.google()
        self.token = id_token(email="ana.new@example.com")

        res = self.google()

        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["user"]["email"], "ana@example.com")

    def test_session_works_and_password_still_works(self):
        self.sign_up()
        token = self.google().json()["session"]["token"]

        self.assertEqual(
            self.client.get("/api/auth/session", headers=self.h(token)).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                "/api/auth/sign-in",
                json={"email": "ana@example.com", "password": "password1"},
            ).status_code,
            200,
        )

    def test_unknown_email_without_invitation_is_refused(self):
        self.sign_up()
        self.token = id_token(sub="google-2", email="eve@example.com")

        res = self.google()

        self.assertEqual(res.status_code, 403)
        self.assertIn("invite", res.json()["detail"])

    def test_invited_email_creates_the_user_and_returns_to_the_invitation(self):
        invitation = self.invite("bia@example.com")
        self.token = id_token(sub="google-bia", email="Bia@Example.com", name="Bia")

        res = self.google()

        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["user"]["email"], "bia@example.com")
        self.assertEqual(res.json()["user"]["name"], "Bia")
        self.assertEqual(res.json()["next"], f"/invite/{invitation}")

    def test_before_setup_google_cannot_create_the_first_user(self):
        res = self.google()

        self.assertEqual(res.status_code, 403)

    def test_unverified_email_is_refused(self):
        self.sign_up()
        self.token = id_token(email_verified=False)

        res = self.google()

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"], "unverified_email")

    def test_a_token_for_another_client_is_refused(self):
        self.sign_up()
        self.token = id_token(aud="someone-else")

        self.assertEqual(self.google().json()["error"], "invalid_token")

    def test_an_expired_token_is_refused(self):
        self.sign_up()
        self.token = id_token(exp=int(time.time()) - 10)

        self.assertEqual(self.google().json()["error"], "invalid_token")

    def test_a_forged_state_is_refused(self):
        self.sign_up()

        res = self.google(state="eyJuZXh0IjoiLyJ9.forged")

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"], "invalid_state")
        self.assertEqual(self.exchanged, [])

    def test_a_stale_state_is_refused(self):
        self.sign_up()
        verifier, query = self.start()

        with mock.patch(
            "app.services.auth.google.time.time", return_value=time.time() + 3600
        ):
            res = self.client.post(
                "/api/auth/google/callback",
                json={
                    "origin": ORIGIN,
                    "code": "c",
                    "state": query["state"][0],
                    "verifier": verifier,
                },
            )

        self.assertEqual(res.json()["error"], "invalid_state")

    def test_google_refusing_the_code_is_a_400(self):
        self.sign_up()

        with mock.patch(
            "app.services.auth.google.http.post_form",
            side_effect=ProviderError("400 from oauth2.googleapis.com"),
        ):
            res = self.google()

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"], "google_refused")

    def test_next_outside_the_site_falls_back(self):
        self.sign_up()

        self.assertEqual(self.google("//evil.example/x").json()["next"], "/projects")
        self.assertEqual(
            self.google("https://evil.example").json()["next"], "/projects"
        )
