"""[release] strategy and changelog: the core's own, or a plugin's through the entry-point groups."""

import unittest
from unittest import mock

from action_platform.abc import ChangelogRenderer, ReleaseStrategy
from action_platform.core import module
from action_platform.core.config import Config
from action_platform.core.exception import ConfigError
from action_platform.core.release import strategies


class Calver(ReleaseStrategy):
    name = "calver"

    def next(self, current, level, prerelease, taken):
        return "2026.09.1"


class Plain(ChangelogRenderer):
    name = "plain"

    def render(self, version, commits):
        return f"## {version}\n" + "\n".join(commits) + "\n"


class StrategiesTest(unittest.TestCase):
    def test_semver_is_the_default_and_bumps(self):
        config = Config()

        self.assertEqual(config.release_strategy.name, "semver")
        self.assertEqual(
            config.release_strategy.next("1.2.3", "minor", False, []), "1.3.0"
        )
        self.assertEqual(
            config.release_strategy.next("1.2.3", "patch", True, ["v1.2.4-rc.1"]),
            "1.2.4-rc.2",
        )
        self.assertTrue(config.release_strategy.is_prerelease("1.0.0-rc.1"))
        self.assertIn("## v1.0.0", config.changelog.render("1.0.0", ["feat: x"]))

    def test_unknown_names_are_config_errors(self):
        with self.assertRaises(ConfigError) as caught:
            strategies.strategy("nope")

        self.assertIn("semver", str(caught.exception))

        with self.assertRaises(ConfigError):
            strategies.renderer("nope")

    def test_a_plugin_strategy_and_renderer_are_picked_by_name(self):
        config = Config()
        config._release_spec = {"strategy": "calver", "changelog": "plain"}

        with (
            mock.patch.object(
                module, "load_release_strategies", return_value={"calver": Calver}
            ),
            mock.patch.object(
                module, "load_changelog_renderers", return_value={"plain": Plain}
            ),
        ):
            self.assertEqual(
                config.release_strategy.next("1.0.0", "patch", False, []), "2026.09.1"
            )
            self.assertEqual(
                config.changelog.render("2026.09.1", ["a"]), "## 2026.09.1\na\n"
            )
