from __future__ import annotations

from unittest import mock

from action_platform.abc import Option, Plugin
from action_platform.core.config import Config
from action_platform.core.exception import ConfigError
from action_platform.core.targets import TargetSpec
from action_platform.plugins import registry
from tests.test_access import GateCase


class Vault(Plugin):
    slug = "vault"
    name = "Vault"
    options = [
        Option("url", "URL", "url", required=True),
        Option("api_key", "API key", "secret", required=True),
        Option("team", "Team"),
    ]

    def register(self, surface):
        pass


def target(**options) -> TargetSpec:
    return TargetSpec(name="vault", kind="vault", options=options)


class PluginConnectionsTest(GateCase):
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
        self.registry_id = self.register()

        from app.core.db.models import App, Organization, Project

        with self.app.state.db.session() as s:
            s.add(Organization(id="org-b", name="Beta", slug="beta"))
            s.add(Project(id="p2", organization_id="org-b", name="Api", slug="api"))
            s.add(App(id="a2", project_id="p2", registry_id="r2", name="api"))
            s.commit()

    def rows(self, organization_id, values):
        from app.services.integrations.plugins import DbOptions

        store = DbOptions(
            self.app.state.db, "vault", organization_id, self.app.state.sealer
        )

        for key, value in values.items():
            store.set(key, value)

    def options(self, organization_id, *allowed):
        from app.services.integrations.plugins import DbOptions
        from app.services.integrations.plugins.connections import SharedConnections

        return DbOptions(
            self.app.state.db,
            "vault",
            organization_id,
            self.app.state.sealer,
            SharedConnections(allowed),
        ).all()

    def guard(self, organization_id, app_id, *allowed):
        from app.core.db.models import App, Organization
        from app.services.deployments import DeployEnv
        from app.services.integrations.plugins.connections import SharedConnections

        with self.app.state.db.session() as s:
            organization = s.get(Organization, organization_id)
            app = s.get(App, app_id)

        return DeployEnv(
            self.app.state.db, self.app.state.sealer, SharedConnections(allowed)
        ).connections(organization, app)

    def test_the_organization_reads_its_own_connection(self):
        self.rows(self.org["id"], {"url": "https://v.test", "api_key": "tok-a"})

        guard = self.guard(self.org["id"], "a1")

        self.assertEqual(guard.env["AP_VAULT_URL"], "https://v.test")
        self.assertEqual(guard.env["AP_VAULT_API_KEY"], "tok-a")
        self.assertEqual(
            self.options(self.org["id"]), {"url": "https://v.test", "api_key": "tok-a"}
        )
        guard.check([target(), target(url="https://V.test/")])

    def test_a_target_in_another_organization_never_gets_this_ones_connection(self):
        self.rows(self.org["id"], {"url": "https://v.test", "api_key": "tok-a"})

        guard = self.guard("org-b", "a2")

        self.assertNotIn("AP_VAULT_API_KEY", guard.env)
        self.assertNotIn("AP_VAULT_URL", guard.env)
        self.assertEqual(self.options("org-b"), {})
        self.assertEqual(self.options("org-b", "*"), {})

        self.rows("org-b", {"url": "https://b.test", "api_key": "tok-b"})
        guard = self.guard("org-b", "a2")

        self.assertEqual(guard.env["AP_VAULT_API_KEY"], "tok-b")

        with self.assertRaisesRegex(ConfigError, "different host"):
            guard.check([target(url="https://v.test")])

    def test_an_app_is_never_resolved_under_an_organization_it_does_not_belong_to(
        self,
    ):
        self.rows(self.org["id"], {"url": "https://v.test", "api_key": "tok-a"})

        with self.assertRaisesRegex(ConfigError, "does not belong"):
            self.guard(self.org["id"], "a2")

    def test_platform_toml_pointing_the_url_at_another_host_is_refused(self):
        self.rows(self.org["id"], {"url": "https://v.test", "api_key": "tok-a"})
        guard = self.guard(self.org["id"], "a1")

        for elsewhere in (
            "https://evil.test",
            "http://v.test",
            "https://v.test:8443",
            "https://v.test.evil.test",
            "https://v.test/other",
        ):
            with self.assertRaisesRegex(ConfigError, "different host"):
                guard.check([target(url=elsewhere)])

    def test_a_deploy_with_a_foreign_url_stops_before_any_target_runs(self):
        from app.repositories.workspace.source import get_registry
        from app.schemas import DeployRequest
        from app.services.deployments import DeploymentsService

        self.rows(self.org["id"], {"url": "https://v.test", "api_key": "tok-a"})
        guard = self.guard(self.org["id"], "a1")
        config = Config.from_dict(
            {
                "deploy": {
                    "targets": [
                        {"name": "vault", "kind": "vault", "url": "https://evil.test"}
                    ]
                }
            }
        )
        configs = mock.Mock()
        configs.config.return_value = config
        service = DeploymentsService(
            get_registry(), env=dict(guard.env), configs=configs, guard=guard
        )

        with (
            mock.patch("app.services.deployments.service.Workspaces") as workspaces,
            mock.patch("app.services.deployments.service.ActionPlatform") as tool,
        ):
            workspaces.return_value.checkout.return_value = (None, self.tmp_path)

            with self.assertRaisesRegex(ConfigError, "different host"):
                service.deploy(self.registry_id, DeployRequest(stage="prod"))

        tool.assert_not_called()

    def test_a_url_in_platform_toml_never_carries_a_credential_it_cannot_check(
        self,
    ):
        self.guard(self.org["id"], "a1").check(
            [target(url="https://own.test", api_key="repo-own")]
        )
        self.rows(self.org["id"], {"api_key": "tok-a"})
        guard = self.guard(self.org["id"], "a1")

        with self.assertRaisesRegex(ConfigError, "no url to check"):
            guard.check([target(url="https://own.test")])

        guard.check([target(url="https://own.test", api_key="repo-own")])

    def test_the_platform_connection_is_refused_unless_the_policy_grants_it(self):
        self.rows("", {"url": "https://shared.test", "api_key": "tok-platform"})

        refused = self.guard(self.org["id"], "a1")

        self.assertNotIn("AP_VAULT_API_KEY", refused.env)
        self.assertEqual(self.options(self.org["id"]), {})

        for allowed in (("acme",), ("*",)):
            granted = self.guard(self.org["id"], "a1", *allowed)

            self.assertEqual(granted.env["AP_VAULT_API_KEY"], "tok-platform")
            self.assertEqual(
                self.options(self.org["id"], *allowed),
                {"url": "https://shared.test", "api_key": "tok-platform"},
            )

        self.assertNotIn("AP_VAULT_API_KEY", self.guard("org-b", "a2", "acme").env)

    def test_an_organization_with_its_own_options_never_mixes_in_the_platforms(
        self,
    ):
        self.rows("", {"url": "https://shared.test", "api_key": "tok-platform"})
        self.rows(self.org["id"], {"url": "https://mine.test"})

        guard = self.guard(self.org["id"], "a1", "*")

        self.assertEqual(guard.env["AP_VAULT_URL"], "https://mine.test")
        self.assertNotIn("AP_VAULT_API_KEY", guard.env)
        self.assertEqual(
            self.options(self.org["id"], "*"), {"url": "https://mine.test"}
        )

    def test_a_credential_in_the_platform_environment_follows_the_policy(self):
        from app.services.integrations.plugins.connections import ConnectionGuard

        ambient = {"AP_VAULT_URL": "https://shared.test", "AP_VAULT_API_KEY": "tok-env"}

        with self.assertRaisesRegex(ConfigError, "AP_PLATFORM_CONNECTIONS"):
            ConnectionGuard({}, False, ambient).check([target()])

        ConnectionGuard({}, True, ambient).check([target()])
        ConnectionGuard({}, True, ambient).check([target(url="https://shared.test")])

        with self.assertRaisesRegex(ConfigError, "different host"):
            ConnectionGuard({}, True, ambient).check([target(url="https://evil.test")])

        with self.assertRaisesRegex(ConfigError, "AP_VAULT_API_KEY"):
            ConnectionGuard({"AP_VAULT_URL": "https://mine.test"}, True, ambient).check(
                [target()]
            )

    def test_the_policy_is_read_from_the_environment(self):
        from app.services.integrations.plugins.connections import SharedConnections

        self.setenv("AP_PLATFORM_CONNECTIONS", " Acme , other ")
        self.rows("", {"url": "https://shared.test", "api_key": "tok-platform"})

        from app.core.db.models import App, Organization
        from app.services.deployments import DeployEnv

        with self.app.state.db.session() as s:
            organization = s.get(Organization, self.org["id"])
            app = s.get(App, "a1")

        env = DeployEnv(self.app.state.db, self.app.state.sealer).for_app(
            organization, app
        )

        self.assertEqual(SharedConnections.from_settings().allowed, ("acme", "other"))
        self.assertEqual(env["AP_VAULT_API_KEY"], "tok-platform")

    def test_an_unknown_target_kind_is_left_to_its_provider(self):
        from app.services.integrations.plugins.connections import ConnectionGuard

        ConnectionGuard({}, False, {"AP_OTHER_TOKEN": "x"}).check(
            [TargetSpec(name="other", kind="other", options={"url": "https://x.test"})]
        )
