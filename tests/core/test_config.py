"""action_platform.core.config — the [deploy] table resolves providers through entry points, lazily."""

from __future__ import annotations

import inspect
import unittest

from action_platform.core import config as config_module
from action_platform.core.config import Config
from action_platform.core.exception import ConfigError
from action_platform.options import SourceTokens
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


class SourceHostTokensTest(TempCase):
    GITHUB = {"source_host": {"kind": "github", "repo": "acme/x"}}
    BITBUCKET = {"source_host": {"kind": "bitbucket", "repo": "acme/x"}}

    def setUp(self):
        super().setUp()
        self.setenv("ACTION_PLATFORM_GITHUB_TOKEN", "env-gh")
        self.setenv("ACTION_PLATFORM_BITBUCKET_TOKEN", "env-bb")
        self.setenv("ACTION_PLATFORM_BITBUCKET_USERNAME", "env-user")

    def test_the_machine_tokens_by_default(self):
        self.assertEqual(Config.from_dict(self.GITHUB).source_host.token, "env-gh")

        host = Config.from_dict(self.BITBUCKET).source_host
        self.assertEqual((host.token, host.username), ("env-bb", "env-user"))

    def test_the_tokens_given(self):
        config = Config.from_dict(self.GITHUB, tokens=SourceTokens(github="given"))

        self.assertEqual(config.source_host.token, "given")

    def test_empty_tokens_mean_none(self):
        host = Config.from_dict(self.BITBUCKET, tokens=SourceTokens()).source_host

        self.assertEqual((host.token, host.username), (None, None))
