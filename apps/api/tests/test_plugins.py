"""`/api/v1/plugins`: the catalog, options, switching, and the jobs that install or remove — the Jenkins model on the hosted platform."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

from action_platform.abc import Plugin
from action_platform.plugins import registry
from action_platform.plugins.state import PluginState
from action_platform.settings import settings
from app.services.templates import published
from app.services.plugins import manager
from tests.test_access import GateCase

INDEX = {
    "plugins": [
        {
            "name": "aws-lambda",
            "pypi": "apx-aws-lambda",
            "latest": "0.1.0",
            "verified": True,
            "needs": ["tool: sam"],
        },
        {
            "name": "sketchy",
            "pypi": "apx-sketchy",
            "latest": "0.0.1",
            "verified": False,
        },
    ]
}


class Lambda(Plugin):
    slug = "aws-lambda"
    description = "fake"

    def register(self, surface):
        pass


class PluginsApiTest(GateCase):
    def setUp(self):
        super().setUp()
        self.plugins_dir = Path(self.tmp_path) / "plugins"
        self.plugins_dir.mkdir()
        self.patch(settings, "PLUGINS_DIR", self.plugins_dir)
        self.patch(published.plugins_index, "cached", INDEX)
        self.patch(published.plugins_index, "fetched_at", float("inf"))
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
        from app.services.plugins.options import DbOptions

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

    def test_catalog_says_it_is_hosted_and_what_waits_for_a_restart(self):
        PluginState.load().mark_restart("aws-lambda")

        rows = self.client.get("/api/v1/plugins", headers=self.h()).json()

        self.assertTrue(rows["hosted"])
        self.assertEqual(rows["restart_pending"], ["aws-lambda"])
        self.assertEqual(
            [p["slug"] for p in rows["plugins"]], ["aws-lambda", "sketchy"]
        )

    def test_install_needs_a_platform_admin(self):
        for path in (
            "aws-lambda/install",
            "aws-lambda/remove",
            "aws-lambda/enable",
            "restart",
        ):
            refused = self.client.post(f"/api/v1/plugins/{path}", headers=self.h())

            self.assertEqual(refused.status_code, 403, path)
            self.assertIn("platform admin", refused.json()["detail"])

    def test_install_queues_a_job_for_verified_plugins_only(self):
        self.patch(settings, "PLATFORM_ADMINS", ("ana@example.com",))
        queued = self.client.post(
            "/api/v1/plugins/aws-lambda/install", headers=self.h()
        )

        self.assertEqual(queued.status_code, 202, queued.text)
        self.assertIn("poll", queued.json())

        refused = self.client.post("/api/v1/plugins/sketchy/install", headers=self.h())

        self.assertEqual(refused.status_code, 400)
        self.assertIn("verified", refused.json()["detail"])

    def test_the_install_job_pips_into_the_volume_and_loads_the_plugin(self):
        seen: list[str] = []

        def fake_install(self, spec):
            seen.append(spec)

        with (
            mock.patch.object(manager.PipInstaller, "install", fake_install),
            mock.patch.object(
                registry.Plugins, "find", staticmethod(lambda known=None: [])
            ),
        ):
            with self.assertRaises(Exception) as caught:
                manager.PluginManager().install(
                    {"slug": "aws-lambda", "spec": "apx-aws-lambda==0.1.0"}
                )

        self.assertEqual(seen, ["apx-aws-lambda==0.1.0"])
        self.assertIn("nothing registered", str(caught.exception))

    def test_the_remove_job_disables_a_loaded_plugin_until_the_restart_forgets_it(self):
        loaded = registry.Loaded(Lambda(), "apx-aws-lambda", "0.1.0")

        with (
            mock.patch.object(manager.PipInstaller, "uninstall", lambda self, p: ""),
            mock.patch.object(
                registry.Plugins, "find", staticmethod(lambda known=None: [loaded])
            ),
        ):
            out = manager.PluginManager().remove(
                {"slug": "aws-lambda", "package": "apx-aws-lambda"}
            )
            rows = self.client.get("/api/v1/plugins", headers=self.h()).json()

        row = next(p for p in rows["plugins"] if p["slug"] == "aws-lambda")

        self.assertTrue(out["restart_required"])
        self.assertEqual(
            (row["installed"], row["enabled"], row["removed"], row["restart_pending"]),
            (False, False, True, True),
        )
        self.assertEqual(rows["restart_pending"], ["aws-lambda"])

        PluginState.load().clear_restart()

        self.assertEqual(PluginState.load().plugins, {})

    def test_switching_an_unknown_plugin_is_a_readable_error(self):
        self.patch(settings, "PLATFORM_ADMINS", ("ana@example.com",))
        res = self.client.post("/api/v1/plugins/nope/enable", headers=self.h())

        self.assertEqual(res.status_code, 400)
        self.assertIn("no plugin", res.json()["detail"])
