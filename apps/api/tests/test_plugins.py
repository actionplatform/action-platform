"""`/api/v1/plugins`: the plugins the image bundles, and the options each organization keeps for them."""

from __future__ import annotations

from unittest import mock

from action_platform.abc import Plugin
from action_platform.plugins import registry
from tests.test_access import GateCase


class Lambda(Plugin):
    slug = "aws-lambda"
    description = "fake"

    def register(self, surface):
        pass


class PluginsApiTest(GateCase):
    def setUp(self):
        super().setUp()
        registry.reset()
        self.addCleanup(registry.reset)

    def test_options_round_trip_through_the_table(self):
        empty = self.client.get("/api/v1/plugins/aws-lambda/options", headers=self.h())

        self.assertEqual(empty.json(), {"options": {}})

        saved = self.client.put(
            "/api/v1/plugins/aws-lambda/options",
            json={"options": {"region": "us-east-1", "retries": 2}},
            headers=self.h(),
        )

        self.assertEqual(saved.json()["options"], {"region": "us-east-1", "retries": 2})

        replaced = self.client.put(
            "/api/v1/plugins/aws-lambda/options",
            json={"options": {"region": "sa-east-1"}},
            headers=self.h(),
        )

        self.assertEqual(replaced.json()["options"], {"region": "sa-east-1"})
        self.assertIsNone(
            registry.installed().options_for("aws-lambda").get("region"),
            "an organization's value is not the platform's default",
        )

    def test_options_belong_to_the_organization_over_platform_defaults(self):
        from app.services.integrations.plugins.options import DbOptions

        db = self.app.state.db
        DbOptions(db, "aws-lambda").set("proxy_url", "https://default.test")
        DbOptions(db, "aws-lambda", "org-a").set("proxy_url", "https://a.test")

        self.assertEqual(
            DbOptions(db, "aws-lambda", "org-a").all(), {"proxy_url": "https://a.test"}
        )
        self.assertEqual(
            DbOptions(db, "aws-lambda", "org-b").all(),
            {"proxy_url": "https://default.test"},
        )
        self.assertEqual(
            DbOptions(db, "aws-lambda", "org-b").get("proxy_url"),
            "https://default.test",
        )

    def test_catalog_lists_the_bundled_plugins_and_the_ones_that_failed_to_load(self):
        loaded = registry.Loaded(Lambda(), "apx-aws-lambda", "0.1.0")

        with mock.patch.object(
            registry.Plugins, "find", staticmethod(lambda known=None: [loaded])
        ):
            registry.FAILURES["broken"] = "ImportError: no module named x"
            self.addCleanup(registry.FAILURES.pop, "broken", None)
            rows = self.client.get("/api/v1/plugins", headers=self.h()).json()

        self.assertEqual(
            [(p["slug"], p["version"], p["error"]) for p in rows["plugins"]],
            [
                ("aws-lambda", "0.1.0", None),
                ("broken", "", "ImportError: no module named x"),
            ],
        )

    def test_install_switch_and_restart_are_gone(self):
        for path in (
            "aws-lambda/install",
            "aws-lambda/remove",
            "aws-lambda/enable",
            "aws-lambda/disable",
            "restart",
        ):
            gone = self.client.post(f"/api/v1/plugins/{path}", headers=self.h())

            self.assertIn(gone.status_code, (404, 405), path)
