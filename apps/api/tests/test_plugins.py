"""`/api/v1/plugins`: the plugins the image bundles, and the options each organization keeps for them."""

from __future__ import annotations

from unittest import mock

from action_platform.abc import Option, Plugin
from action_platform.plugins import registry
from tests.test_access import GateCase


class Lambda(Plugin):
    slug = "aws-lambda"
    name = "AWS Lambda"
    description = "fake"
    options = [
        Option(
            "role_arn",
            "AWS account",
            required=True,
            action_label="Connect AWS",
            action_url="https://console.aws.amazon.com/?issuer={issuer}",
            action_copy="connect {issuer} {organization}",
        )
    ]

    def register(self, surface):
        pass


class PluginsApiTest(GateCase):
    def setUp(self):
        super().setUp()
        registry.reset()
        self.addCleanup(registry.reset)

    def test_options_round_trip_through_the_table(self):
        empty = self.client.get("/api/v1/plugins/aws-lambda/options", headers=self.h())

        self.assertEqual(empty.json(), {"options": {}, "secrets": []})

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
        DbOptions(db, "aws-lambda").set("role_arn", "arn:aws:iam::1:role/default")
        DbOptions(db, "aws-lambda", "org-a").set("role_arn", "arn:aws:iam::2:role/a")

        self.assertEqual(
            DbOptions(db, "aws-lambda", "org-a").all(),
            {"role_arn": "arn:aws:iam::2:role/a"},
        )
        self.assertEqual(
            DbOptions(db, "aws-lambda", "org-b").all(),
            {"role_arn": "arn:aws:iam::1:role/default"},
        )
        self.assertEqual(
            DbOptions(db, "aws-lambda", "org-b").get("role_arn"),
            "arn:aws:iam::1:role/default",
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
        self.assertEqual(rows["plugins"][0]["name"], "AWS Lambda")
        self.assertEqual(
            rows["plugins"][0]["options"],
            [
                {
                    "key": "role_arn",
                    "label": "AWS account",
                    "kind": "text",
                    "help": "",
                    "required": True,
                    "action_label": "Connect AWS",
                    "action_url": "https://console.aws.amazon.com/?issuer={issuer}",
                    "action_copy": "connect {issuer} {organization}",
                }
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


class Vault(Plugin):
    slug = "vault"
    name = "Vault"
    options = [
        Option("url", "URL", "url", required=True),
        Option("api_key", "API key", "secret", required=True),
    ]

    def register(self, surface):
        pass


class PluginSecretsTest(GateCase):
    def setUp(self):
        super().setUp()
        registry.reset()
        self.addCleanup(registry.reset)
        loaded = registry.Loaded(Vault(), "apx-vault", "0.1.0")
        patcher = mock.patch.object(
            registry.Plugins, "find", staticmethod(lambda known=None: [loaded])
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def raw(self, key):
        from app.core.db.models import PluginOption

        with self.app.state.db.session() as s:
            row = s.get(PluginOption, (self.org["id"], "vault", key))

            return row.value if row else None

    def test_a_secret_is_sealed_at_rest_and_never_answered(self):
        saved = self.client.put(
            "/api/v1/plugins/vault/options",
            json={"options": {"url": "https://v.test", "api_key": "tok-123"}},
            headers=self.h(),
        ).json()

        self.assertEqual(
            saved, {"options": {"url": "https://v.test"}, "secrets": ["api_key"]}
        )
        self.assertNotIn("tok-123", self.raw("api_key"))
        self.assertIn("$sealed", self.raw("api_key"))

        read = self.client.get("/api/v1/plugins/vault/options", headers=self.h())

        self.assertNotIn("tok-123", read.text)

    def test_a_form_that_leaves_the_secret_empty_keeps_it(self):
        self.client.put(
            "/api/v1/plugins/vault/options",
            json={"options": {"url": "https://v.test", "api_key": "tok-123"}},
            headers=self.h(),
        )

        for body in (
            {"url": "https://w.test"},
            {"url": "https://w.test", "api_key": ""},
        ):
            kept = self.client.put(
                "/api/v1/plugins/vault/options",
                json={"options": body},
                headers=self.h(),
            ).json()

            self.assertEqual(kept["secrets"], ["api_key"])

        cleared = self.client.put(
            "/api/v1/plugins/vault/options",
            json={"options": {"url": "https://w.test", "api_key": None}},
            headers=self.h(),
        ).json()

        self.assertEqual(cleared["secrets"], [])

    def test_a_deploy_job_gets_the_secret_opened(self):
        from app.services.deployments.env import DeployEnv
        from app.services.integrations.plugins import DbOptions

        DbOptions(
            self.app.state.db, "vault", self.org["id"], self.app.state.sealer
        ).set("api_key", "tok-123")
        org = mock.Mock(id=self.org["id"], slug="acme")
        app = mock.Mock(project_id="none", name="orders")

        env = DeployEnv(self.app.state.db, self.app.state.sealer).for_app(org, app)

        self.assertEqual(env["AP_VAULT_API_KEY"], "tok-123")

    def test_secrets_stored_in_plain_text_are_sealed_at_start(self):
        from app.core.db.models import PluginOption
        from app.services.integrations.plugins import reseal

        with self.app.state.db.session() as s:
            s.add(
                PluginOption(
                    organization_id=self.org["id"],
                    plugin="vault",
                    key="api_key",
                    value='"legacy-tok"',
                )
            )
            s.commit()

        self.assertEqual(reseal(self.app.state.db, self.app.state.sealer), 1)
        self.assertNotIn("legacy-tok", self.raw("api_key"))
        self.assertEqual(reseal(self.app.state.db, self.app.state.sealer), 0)
