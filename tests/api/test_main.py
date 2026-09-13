"""action_platform.api.main — the app factory, its open endpoints and the shared token."""

from __future__ import annotations

from tests.api.support import ApiCase, TestClient


class StaticEndpointsTest(ApiCase):
    def test_version_and_rules(self):
        self.assertIn("version", self.client.get("/api/version").json())
        rules = self.client.get("/api/gitflow/rules").json()
        self.assertIn("feature", rules["kinds"])
        self.assertIn("main", rules["protected"])

    def test_unknown_app_is_400(self):
        self.assertEqual(self.client.get("/api/apps/nope").status_code, 400)


class ApiTokenTest(ApiCase):
    def test_guards_every_route_but_version(self):
        from action_platform.api.main import build

        guarded = TestClient(build(token="s3cret"))

        self.assertEqual(guarded.get("/api/version").status_code, 200)
        self.assertEqual(guarded.get("/api/apps").status_code, 401)
        self.assertEqual(
            guarded.get(
                "/api/apps", headers={"authorization": "Bearer nope"}
            ).status_code,
            401,
        )
        self.assertEqual(
            guarded.get(
                "/api/apps", headers={"authorization": "Bearer s3cret"}
            ).status_code,
            200,
        )


class SentryTest(ApiCase):
    def test_initialises_only_with_a_dsn(self):
        import sentry_sdk

        from action_platform.observability import observe

        seen: dict = {}
        self.patch(sentry_sdk, "init", lambda **kw: seen.update(kw))

        self.assertFalse(observe("api", ""))
        self.assertEqual(seen, {})

        self.patch(sentry_sdk, "set_tag", lambda *a: None)
        self.assertTrue(observe("api", "https://key@o1.ingest.sentry.io/1"))
        self.assertEqual(seen["dsn"], "https://key@o1.ingest.sentry.io/1")
        self.assertTrue(seen["release"].startswith("api@"))
        self.assertFalse(seen["send_default_pii"])
