"""action_platform.core.config — the [deploy] table resolves providers through entry points, lazily."""

from __future__ import annotations

import inspect
import unittest

from action_platform.core import config as config_module
from action_platform.core.config import Config
from action_platform.core.exception import ConfigError
from tests.support import TempCase

BASE = '[project]\nname = "my-api"\nlanguage = "python"\n'


class FakeTarget:
    name = "fake"

    def __init__(self, region: str = "us-east-1") -> None:
        self.region = region


class DeployConfigTest(TempCase):
    def config(self, deploy: str) -> Config:
        path = self.tmp_path / "platform.toml"
        path.write_text(BASE + deploy)
        return Config.from_toml(path)

    def test_no_deploy_section(self):
        self.assertEqual(self.config("").deploy, [])

    def test_target_resolved_from_entry_points(self):
        self.patch(
            "action_platform.core.module.load_deploy_targets",
            value=lambda: {"fake": FakeTarget},
        )

        (target,) = self.config(
            '[deploy]\ntarget = "fake"\nregion = "sa-east-1"\n'
        ).deploy

        self.assertIsInstance(target, FakeTarget)
        self.assertEqual(target.region, "sa-east-1")

    def test_unknown_target(self):
        self.patch("action_platform.core.module.load_deploy_targets", value=lambda: {})

        with self.assertRaisesRegex(ConfigError, "no provider installed"):
            self.config('[deploy]\ntarget = "aws/lambda"\n').deploy

    def test_loading_never_needs_a_provider(self):
        self.patch("action_platform.core.module.load_deploy_targets", value=lambda: {})

        config = self.config('[deploy]\ntarget = "aws/lambda"\n')

        self.assertEqual(config.project_name, "my-api")
        with self.assertRaises(ConfigError):
            config.deploy


class ModuleIsolationTest(unittest.TestCase):
    def test_config_module_has_no_provider_imports(self):
        src = inspect.getsource(config_module)

        self.assertNotIn("deploy_aws", src)
        self.assertNotIn("deploy_docker", src)
