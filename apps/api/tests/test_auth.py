"""Auth owned by the API: accounts, sessions and cookies, the device flow, scoped tokens, rate limits."""

from __future__ import annotations

import unittest
from datetime import timedelta

from action_platform.testing.fixtures import TempCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

GRANT = "urn:ietf:params:oauth:grant-type:device_code"


@unittest.skipUnless(TestClient, "fastapi is not installed")
class AuthCase(TempCase):
    def setUp(self):
        super().setUp()
        from app.api.app import build
        from app.api.routes.auth.support import LIMITS

        self.setenv("AP_HOME", str(self.tmp_path / "home"))
        self.setenv("AP_ALLOW_UNAUTHENTICATED", "1")
        for limiter in LIMITS.values():
            limiter.hits.clear()
        self.app = build(
            database_url=f"sqlite:///{self.tmp_path / 'auth.db'}",
            auth_secret="s3cret",
            public_url="https://ap.example.com",
        )
        self.client = TestClient(self.app)

    def sign_up(
        self, name="Ana", email="ana@example.com", password="password1", **extra
    ):
        return self.client.post(
            "/api/auth/sign-up",
            json={"name": name, "email": email, "password": password, **extra},
        )

    def owner(self) -> dict:
        signed = self.sign_up().json()
        token = signed["session"]["token"]
        org = self.client.post(
            "/api/auth/organizations",
            json={"name": "Acme", "slug": "acme"},
            headers=self.h(token),
        )
        assert org.status_code == 201, org.text
        return {"token": token, "org": org.json(), "user": signed["user"]}

    @staticmethod
    def h(token: str) -> dict:
        return {"X-Session-Token": token}


class AccountsTest(AuthCase):
    def test_first_sign_up_opens_then_closes(self):
        first = self.sign_up()
        self.assertEqual(first.status_code, 201, first.text)
        self.assertIn("cookie", first.json()["session"])
        second = self.sign_up(email="bob@example.com")
        self.assertEqual(second.status_code, 403)
        self.assertEqual(second.json()["error"], "forbidden")

    def test_weak_password_and_duplicate_email(self):
        self.assertEqual(self.sign_up(password="short").status_code, 400)
        self.sign_up()
        self.assertEqual(
            self.client.get("/api/auth/status").json(),
            {"configured": True, "users": 1, "organizations": 0},
        )

    def test_sign_in_with_better_auth_hash(self):
        from app.core.db.models import Account, User

        with self.app.state.db.session() as s:
            s.add(User(id="u1", name="Old", email="old@example.com"))
            s.add(
                Account(
                    id="a1",
                    account_id="u1",
                    provider_id="credential",
                    user_id="u1",
                    password="738117cc47e41af13ba04c5943d8c977:d6a0c4aac56a32c947fef24eb1c61b2c8ac5dd953334e398aa87c71f09bbbd0664f909002ab5022039592b27261a2e584b684243dbd914f34874ebdbb3cfc93b",
                )
            )
        ok = self.client.post(
            "/api/auth/sign-in",
            json={"email": "old@example.com", "password": "pässword1"},
        )
        self.assertEqual(ok.status_code, 200, ok.text)
        bad = self.client.post(
            "/api/auth/sign-in", json={"email": "old@example.com", "password": "nope"}
        )
        self.assertEqual(bad.status_code, 401)
        self.assertEqual(bad.json()["error"], "invalid_credentials")

    def test_session_by_cookie_and_by_token_then_sign_out(self):
        signed = self.sign_up().json()
        cookie = signed["session"]["cookie"]
        token = signed["session"]["token"]
        by_cookie = self.client.get(
            "/api/auth/session", headers={"X-Session-Cookie": cookie}
        )
        self.assertEqual(by_cookie.status_code, 200, by_cookie.text)
        self.assertEqual(by_cookie.json()["user"]["email"], "ana@example.com")
        self.assertEqual(
            self.client.get(
                "/api/auth/session", headers={"X-Session-Cookie": cookie[:-3] + "AAA"}
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.post("/api/auth/sign-out", headers=self.h(token)).status_code,
            204,
        )
        self.assertEqual(
            self.client.get("/api/auth/session", headers=self.h(token)).status_code, 401
        )

    def test_cookie_matches_better_call_signature(self):
        signed = self.sign_up().json()["session"]
        self.assertTrue(signed["cookie"].startswith(signed["token"] + "."))
        self.assertTrue(signed["cookie"].endswith("%3D"))

    def test_sessions_listed_and_revoked(self):
        token = self.sign_up().json()["session"]["token"]
        other = self.client.post(
            "/api/auth/sign-in",
            json={
                "email": "ana@example.com",
                "password": "password1",
                "user_agent": "Firefox",
            },
        ).json()
        rows = self.client.get("/api/auth/sessions", headers=self.h(token)).json()
        self.assertEqual([r["current"] for r in rows], [True, False])
        self.assertEqual(
            self.client.delete(
                f"/api/auth/sessions/{other['session']['id']}", headers=self.h(token)
            ).status_code,
            204,
        )
        self.assertEqual(
            self.client.get(
                "/api/auth/session", headers=self.h(other["session"]["token"])
            ).status_code,
            401,
        )

    def test_invitation_opens_sign_up_for_that_email_only(self):
        from app.services.auth.service import now
        from app.core.db.models import Invitation

        owner = self.owner()
        with self.app.state.db.session() as s:
            s.add(
                Invitation(
                    id="i1",
                    organization_id=owner["org"]["id"],
                    email="bob@example.com",
                    role="developer",
                    status="pending",
                    expires_at=now() + timedelta(days=1),
                    inviter_id=owner["user"]["id"],
                )
            )
        wrong = self.sign_up(name="Eve", email="eve@example.com", invitation_id="i1")
        self.assertEqual(wrong.status_code, 403)
        right = self.sign_up(name="Bob", email="bob@example.com", invitation_id="i1")
        self.assertEqual(right.status_code, 201, right.text)


class OrganizationsTest(AuthCase):
    def test_create_sets_active_and_owner_role(self):
        owner = self.owner()
        me = self.client.get("/api/auth/session", headers=self.h(owner["token"])).json()
        self.assertEqual(me["organization"]["slug"], "acme")
        self.assertEqual(me["role"], "owner")
        self.assertTrue(me["grants"]["org.manage"])
        dup = self.client.post(
            "/api/auth/organizations",
            json={"name": "Acme 2", "slug": "acme"},
            headers=self.h(owner["token"]),
        )
        self.assertEqual(dup.status_code, 409)

    def test_active_organization_requires_membership(self):
        owner = self.owner()
        refused = self.client.post(
            "/api/auth/session/organization",
            json={"organization_id": "nope"},
            headers=self.h(owner["token"]),
        )
        self.assertEqual(refused.status_code, 403)


class MembersTest(AuthCase):
    def test_owner_adds_member_with_password_and_sign_in_works(self):
        owner = self.owner()
        added = self.client.post(
            "/api/auth/members",
            json={
                "organization_id": owner["org"]["id"],
                "name": "Bob",
                "email": "Bob@example.com",
                "password": "password2",
                "role": "developer",
            },
            headers=self.h(owner["token"]),
        )
        self.assertEqual(added.status_code, 201, added.text)
        self.assertFalse(added.json()["existed"])
        signed = self.client.post(
            "/api/auth/sign-in",
            json={"email": "bob@example.com", "password": "password2"},
        )
        self.assertEqual(signed.status_code, 200)
        me = self.client.get(
            "/api/auth/session", headers=self.h(signed.json()["session"]["token"])
        ).json()
        self.assertEqual(me["role"], "developer")
        again = self.client.post(
            "/api/auth/members",
            json={
                "organization_id": owner["org"]["id"],
                "name": "",
                "email": "bob@example.com",
                "password": "",
                "role": "viewer",
            },
            headers=self.h(owner["token"]),
        )
        self.assertEqual(again.status_code, 409)
        refused = self.client.post(
            "/api/auth/members",
            json={
                "organization_id": owner["org"]["id"],
                "name": "Eve",
                "email": "eve@example.com",
                "password": "password3",
                "role": "viewer",
            },
            headers=self.h(signed.json()["session"]["token"]),
        )
        self.assertEqual(refused.status_code, 403)


class DeviceFlowTest(AuthCase):
    def start(self, scope="read write"):
        res = self.client.post(
            "/api/auth/device/code",
            json={"client_id": "action-platform-cli/1.0", "scope": scope},
        )
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()

    def poll(self, device_code: str):
        return self.client.post(
            "/api/auth/device/token",
            json={
                "grant_type": GRANT,
                "device_code": device_code,
                "client_id": "action-platform-cli/1.0",
            },
        )

    def test_pending_then_approved_then_used_once(self):
        owner = self.owner()
        start = self.start()
        self.assertEqual(
            start["verification_uri_complete"],
            f"https://ap.example.com/device?user_code={start['user_code']}",
        )
        self.assertEqual(
            self.poll(start["device_code"]).json()["error"], "authorization_pending"
        )
        self.assertEqual(self.poll(start["device_code"]).json()["error"], "slow_down")
        seen = self.client.get(
            "/api/auth/device",
            params={"user_code": start["user_code"]},
            headers=self.h(owner["token"]),
        ).json()
        self.assertEqual(
            (seen["status"], seen["requested"]), ("pending", ["read", "write"])
        )
        approved = self.client.post(
            "/api/auth/device/approve",
            json={
                "user_code": start["user_code"],
                "grant": {
                    "scope": ["read", "write"],
                    "organization_id": owner["org"]["id"],
                },
            },
            headers=self.h(owner["token"]),
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        with self.app.state.db.session() as s:
            from app.core.db.models import DeviceCode

            s.query(DeviceCode).update({"polling_interval": 0})
        token = self.poll(start["device_code"])
        self.assertEqual(token.status_code, 200, token.text)
        self.assertEqual(token.json()["scope"], f"read write org:{owner['org']['id']}")
        self.assertEqual(
            self.client.get(
                "/api/auth/session", headers=self.h(token.json()["access_token"])
            ).status_code,
            200,
        )
        self.assertEqual(
            self.poll(start["device_code"]).json()["error"], "invalid_grant"
        )

    def test_denied(self):
        owner = self.owner()
        start = self.start()
        self.client.post(
            "/api/auth/device/deny",
            json={"user_code": start["user_code"]},
            headers=self.h(owner["token"]),
        )
        with self.app.state.db.session() as s:
            from app.core.db.models import DeviceCode

            s.query(DeviceCode).update({"polling_interval": 0})
        self.assertEqual(
            self.poll(start["device_code"]).json()["error"], "access_denied"
        )

    def test_grant_is_cut_to_the_role(self):
        from app.core.db.models import Member

        owner = self.owner()
        with self.app.state.db.session() as s:
            s.query(Member).update({"role": "viewer"})
        start = self.start("read write admin")
        refused = self.client.post(
            "/api/auth/device/approve",
            json={
                "user_code": start["user_code"],
                "grant": {
                    "scope": ["read", "admin"],
                    "organization_id": owner["org"]["id"],
                },
            },
            headers=self.h(owner["token"]),
        )
        self.assertEqual(refused.status_code, 200, refused.text)
        seen = self.client.get(
            "/api/auth/device",
            params={"user_code": start["user_code"]},
            headers=self.h(owner["token"]),
        ).json()
        self.assertEqual(seen["grant"]["scope"], ["read"])

    def test_unknown_code_is_404_for_the_browser(self):
        owner = self.owner()
        self.assertEqual(
            self.client.get(
                "/api/auth/device",
                params={"user_code": "NOPE1234"},
                headers=self.h(owner["token"]),
            ).status_code,
            404,
        )


class TokensTest(AuthCase):
    def test_issue_verify_list_revoke(self):
        owner = self.owner()
        issued = self.client.post(
            "/api/auth/tokens",
            json={
                "name": "laptop",
                "scope": "read write admin",
                "organization_id": owner["org"]["id"],
            },
            headers=self.h(owner["token"]),
        )
        self.assertEqual(issued.status_code, 201, issued.text)
        raw = issued.json()["token"]
        self.assertEqual(raw.count("."), 2)
        claims = self.client.post(
            "/api/auth/tokens/verify", json={"token": raw, "client": "Claude Code/1.2"}
        )
        self.assertEqual(claims.status_code, 200, claims.text)
        self.assertEqual(
            (
                claims.json()["scope"],
                claims.json()["role"],
                claims.json()["all_organizations"],
            ),
            (["read", "write", "admin"], "owner", False),
        )
        listed = self.client.get(
            "/api/auth/tokens", headers=self.h(owner["token"])
        ).json()
        self.assertEqual(listed[0]["clients"][0]["name"], "Claude Code/1.2")
        self.assertEqual(listed[0]["organization"]["name"], "Acme")
        self.assertEqual(
            self.client.delete(
                f"/api/auth/tokens/{listed[0]['id']}", headers=self.h(owner["token"])
            ).status_code,
            204,
        )
        self.assertEqual(
            self.client.post(
                "/api/auth/tokens/verify", json={"token": raw}
            ).status_code,
            401,
        )

    def test_token_signed_with_the_web_apps_key(self):
        from app.core.auth import jwt
        from app.core.auth.secrets import Secrets

        owner = self.owner()
        raw = self.client.post(
            "/api/auth/tokens",
            json={"name": "x", "scope": "read org:*"},
            headers=self.h(owner["token"]),
        ).json()["token"]
        claims = jwt.decode(
            raw,
            Secrets("s3cret").subkey("api-token"),
            "action-platform",
            "action-platform/api/v1",
        )
        self.assertEqual(claims["sub"], owner["user"]["id"])
        self.assertNotIn("org", claims)
        self.assertIsNone(
            jwt.decode(
                raw,
                Secrets("other").subkey("api-token"),
                "action-platform",
                "action-platform/api/v1",
            )
        )

    def test_no_organization_means_the_active_one(self):
        owner = self.owner()
        issued = self.client.post(
            "/api/auth/tokens",
            json={"name": "x", "scope": "read"},
            headers=self.h(owner["token"]),
        ).json()
        claims = self.client.post(
            "/api/auth/tokens/verify", json={"token": issued["token"]}
        ).json()
        self.assertEqual(claims["organization"]["id"], owner["org"]["id"])

    def test_scope_cut_to_role_and_read_required(self):
        from app.core.db.models import Member

        owner = self.owner()
        with self.app.state.db.session() as s:
            s.query(Member).update({"role": "developer"})
        cut = self.client.post(
            "/api/auth/tokens",
            json={"name": "x", "scope": "read release admin"},
            headers=self.h(owner["token"]),
        )
        self.assertEqual(cut.json()["scope"], ["read"])
        none = self.client.post(
            "/api/auth/tokens",
            json={"name": "x", "scope": "admin"},
            headers=self.h(owner["token"]),
        )
        self.assertEqual(none.status_code, 403)

    def test_tampered_token_is_refused(self):
        owner = self.owner()
        raw = self.client.post(
            "/api/auth/tokens",
            json={"name": "x", "scope": "read"},
            headers=self.h(owner["token"]),
        ).json()["token"]
        head, body, sig = raw.split(".")
        self.assertEqual(
            self.client.post(
                "/api/auth/tokens/verify", json={"token": f"{head}.{body}x.{sig}"}
            ).status_code,
            401,
        )


class LimitsTest(AuthCase):
    def test_sign_in_is_rate_limited_per_ip(self):
        self.sign_up()
        for _ in range(10):
            self.client.post(
                "/api/auth/sign-in",
                json={"email": "ana@example.com", "password": "wrong"},
                headers={"X-Forwarded-For": "10.0.0.9"},
            )
        blocked = self.client.post(
            "/api/auth/sign-in",
            json={"email": "ana@example.com", "password": "password1"},
            headers={"X-Forwarded-For": "10.0.0.9"},
        )
        self.assertEqual(blocked.status_code, 429)
        spoofed = self.client.post(
            "/api/auth/sign-in",
            json={"email": "ana@example.com", "password": "password1"},
            headers={"X-Forwarded-For": "10.0.0.10"},
        )
        self.assertEqual(spoofed.status_code, 429)

        from unittest import mock

        from app.api.routes.auth import support

        with mock.patch.object(support, "_trusted", return_value=True):
            other = self.client.post(
                "/api/auth/sign-in",
                json={"email": "ana@example.com", "password": "password1"},
                headers={"X-Forwarded-For": "1.2.3.4, 10.0.0.10"},
            )

        self.assertEqual(other.status_code, 200)

    def test_without_secret_auth_is_503(self):
        from app.api.app import build

        app = build(
            database_url=f"sqlite:///{self.tmp_path / 'nosecret.db'}", auth_secret=""
        )
        res = TestClient(app).post(
            "/api/auth/sign-in", json={"email": "a@b.c", "password": "x"}
        )
        self.assertEqual(res.status_code, 503)
