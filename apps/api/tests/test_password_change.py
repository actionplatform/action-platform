"""Changing your own password: the current one is checked, the other sessions and API tokens end, this session stays."""

from __future__ import annotations

from tests.test_auth import AuthCase


class PasswordChangeTest(AuthCase):
    def change(self, token, current="password1", new="new-password1"):
        return self.client.post(
            "/api/auth/password/change",
            json={"current_password": current, "new_password": new},
            headers=self.h(token),
        )

    def sign_in(self, password, email="ana@example.com"):
        return self.client.post(
            "/api/auth/sign-in", json={"email": email, "password": password}
        )

    def alive(self, token):
        return self.client.get("/api/auth/session", headers=self.h(token)).status_code

    def verify(self, token):
        return self.client.post(
            "/api/auth/tokens/verify", json={"token": token}
        ).status_code

    def test_changes_the_password_and_keeps_this_session(self):
        owner = self.owner()

        self.assertEqual(self.change(owner["token"]).status_code, 204)
        self.assertEqual(self.alive(owner["token"]), 200)
        self.assertEqual(self.sign_in("password1").status_code, 401)
        self.assertEqual(self.sign_in("new-password1").status_code, 200)

    def test_ends_the_other_sessions(self):
        owner = self.owner()
        other = self.sign_in("password1").json()["session"]["token"]

        self.assertEqual(self.change(owner["token"]).status_code, 204)
        self.assertEqual(self.alive(owner["token"]), 200)
        self.assertEqual(self.alive(other), 401)

    def test_revokes_api_tokens(self):
        owner = self.owner()
        issued = self.client.post(
            "/api/auth/tokens",
            json={
                "name": "cli",
                "scope": "read",
                "organization_id": owner["org"]["id"],
            },
            headers=self.h(owner["token"]),
        ).json()["token"]

        self.assertEqual(self.verify(issued), 200)
        self.assertEqual(self.change(owner["token"]).status_code, 204)
        self.assertEqual(self.verify(issued), 401)

    def test_a_wrong_current_password_changes_nothing(self):
        owner = self.owner()
        other = self.sign_in("password1").json()["session"]["token"]

        refused = self.change(owner["token"], current="not-it")

        self.assertEqual(refused.status_code, 400)
        self.assertEqual(refused.json()["error"], "wrong_password")
        self.assertEqual(self.alive(other), 200)
        self.assertEqual(self.sign_in("password1").status_code, 200)
        self.assertEqual(self.sign_in("new-password1").status_code, 401)

    def test_a_weak_new_password_changes_nothing(self):
        owner = self.owner()

        weak = self.change(owner["token"], new="short")

        self.assertEqual(weak.status_code, 400)
        self.assertEqual(weak.json()["error"], "weak_password")
        self.assertEqual(self.sign_in("password1").status_code, 200)

    def test_needs_a_session(self):
        self.owner()

        refused = self.client.post(
            "/api/auth/password/change",
            json={"current_password": "password1", "new_password": "new-password1"},
        )

        self.assertEqual(refused.status_code, 401)

    def test_is_rate_limited(self):
        owner = self.owner()
        codes = [
            self.change(owner["token"], current="nope").status_code for _ in range(6)
        ]

        self.assertEqual(codes[:5], [400] * 5)
        self.assertEqual(codes[5], 429)
