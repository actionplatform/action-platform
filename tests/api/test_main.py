"""action_platform.api.main — the app factory, its open endpoints and the shared token."""

from __future__ import annotations

import unittest
import urllib.error
from unittest import mock

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
    def test_refuses_to_start_open_unless_asked(self):
        from action_platform.api.main import build
        from action_platform.core.exception import ConfigError
        from action_platform.settings import settings

        self.patch(settings, "ALLOW_UNAUTHENTICATED_API", False)

        with self.assertRaisesRegex(ConfigError, "AP_API_TOKEN"):
            build(token="", database_url="sqlite://")

    def test_guards_every_route_but_version(self):
        from action_platform.api.main import build

        guarded = TestClient(build(token="s3cret", database_url="sqlite://"))

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


class CatalogIndexTest(ApiCase):
    def test_matrix_prefers_the_published_index(self):
        from action_platform.api.services import catalog
        from action_platform.api.services.catalog import published
        from action_platform.settings import settings

        self.patch(settings, "TEMPLATES_DIR", None)
        data = {
            "types": [{"id": "web", "label": "Web application", "description": "APIs"}],
            "stacks": [
                {"id": "python", "label": "Python", "icon": "assets/icons/python.svg"}
            ],
            "projects": [
                {
                    "id": "web/python/fastapi",
                    "type": "web",
                    "stack": "python",
                    "template": "fastapi",
                    "framework": "FastAPI",
                    "language": "python",
                    "description": "FastAPI",
                    "default": True,
                    "version": "0.1.0",
                    "path": "projects/web/python/fastapi",
                    "url": "https://github.com/actionplatform/templates/tree/main/projects/web/python/fastapi",
                    "icons": {
                        "language": "assets/icons/python.svg",
                        "framework": "assets/icons/fastapi.svg",
                    },
                }
            ],
            "clouds": [
                {
                    "id": "docker",
                    "description": "Docker",
                    "types": ["web"],
                    "languages": ["python"],
                    "icon": "assets/icons/docker.svg",
                }
            ],
            "services": [],
        }
        fake = published.TemplatesIndex(
            "https://example.com/templates/index.json", ttl=600
        )
        fake.cached = data
        fake.fetched_at = 10**12
        self.patch(catalog, "index", fake)
        self.patch(catalog, "load_matrix", lambda: (None, catalog.Matrix()))

        matrix = self.client.get("/api/matrix").json()

        self.assertEqual(
            matrix["types"],
            [{"id": "web", "label": "Web application", "description": "APIs"}],
        )
        self.assertEqual(
            matrix["stacks"][0]["icon"],
            "https://example.com/templates/assets/icons/python.svg",
        )
        project = matrix["projects"][0]
        self.assertEqual(
            (project["framework"], project["icon"], project["path"]),
            (
                "FastAPI",
                "https://example.com/templates/assets/icons/fastapi.svg",
                "projects/web/python/fastapi",
            ),
        )
        self.assertEqual(
            matrix["clouds"][0]["icon"],
            "https://example.com/templates/assets/icons/docker.svg",
        )

    def test_matrix_falls_back_to_the_checkout_when_the_index_is_down(self):
        from action_platform.api.services import catalog
        from action_platform.api.services.catalog import published

        from action_platform.settings import settings
        from tests.support import template_repo

        self.patch(settings, "TEMPLATES_DIR", str(template_repo(self.tmp_path)))
        dead = published.TemplatesIndex("http://127.0.0.1:9/index.json", ttl=600)
        self.patch(catalog, "index", dead)

        response = self.client.get("/api/matrix")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(
            any(p["template"] == "fastapi" for p in response.json()["projects"])
        )


class TemplatesIndexTest(unittest.TestCase):
    def test_revalidates_with_etag_and_keeps_cache_on_304(self):
        from action_platform.api.services.catalog import published

        calls = []

        class Response:
            def __init__(self, body, etag):
                self.body = body
                self.headers = {"etag": etag}

            def read(self):
                return self.body

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        def urlopen(request, timeout):
            calls.append(request.get_header("If-none-match"))

            if len(calls) == 1:
                return Response(b'{"projects": [1]}', '"v1"')

            if len(calls) == 2:
                raise urllib.error.HTTPError(request.full_url, 304, "", {}, None)

            return Response(b'{"projects": [1, 2]}', '"v2"')

        fake = published.TemplatesIndex("https://example.com/index.json", ttl=0)

        with mock.patch.object(published.urllib.request, "urlopen", urlopen):
            self.assertEqual(fake.get(), {"projects": [1]})
            self.assertEqual(fake.get(), {"projects": [1]})
            self.assertEqual(fake.get(), {"projects": [1, 2]})

        self.assertEqual(calls, [None, '"v1"', '"v1"'])
        self.assertEqual(fake.etag, '"v2"')
