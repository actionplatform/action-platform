import unittest

from action_platform.core.config import Config
from action_platform.core.exception import ConfigError
from action_platform.core.scopes import (
    CRITICALITIES,
    accepts,
    parse_scopes,
    shape_check,
    shape_of,
)


class ShapeTest(unittest.TestCase):
    def test_shape_from_version_and_branch(self):
        self.assertEqual(shape_of("1.4.0"), "stable")
        self.assertEqual(shape_of("v1.4.0"), "stable")
        self.assertEqual(shape_of("1.4.0-rc.2"), "candidate")
        self.assertEqual(shape_of("1.4.0+build.5"), "stable")
        self.assertEqual(shape_of("1.4.1", branch="hotfix/123-login"), "hotfix")
        self.assertEqual(shape_of("1.4.1-rc.1", branch="hotfix/123"), "hotfix")


class PolicyTest(unittest.TestCase):
    def test_default_policy(self):
        table = {
            c: [s for s in ("candidate", "stable", "hotfix") if accepts(c, s)]
            for c in CRITICALITIES
        }

        self.assertEqual(table["test"], ["candidate", "stable", "hotfix"])
        self.assertEqual(table["low"], ["candidate", "stable", "hotfix"])
        self.assertEqual(table["medium"], ["stable", "hotfix"])
        self.assertEqual(table["high"], ["stable", "hotfix"])
        self.assertEqual(table["critical"], ["stable", "hotfix"])

    def test_an_organization_may_change_a_level(self):
        self.assertFalse(accepts("test", "stable", {"test": {"candidate"}}))
        self.assertTrue(
            accepts("medium", "candidate", {"medium": {"candidate", "stable"}})
        )

    def test_unknown_values_are_refused(self):
        with self.assertRaises(ConfigError):
            accepts("urgent", "stable")

        with self.assertRaises(ConfigError):
            accepts("low", "beta")

    def test_the_check_names_the_rule(self):
        scopes = parse_scopes({"scopes": [{"name": "prod", "criticality": "high"}]})

        blocked = shape_check(scopes[0], "1.4.0-rc.2", "candidate")
        allowed = shape_check(scopes[0], "1.4.1", "hotfix")

        self.assertFalse(blocked.ok)
        self.assertTrue(blocked.blocking)
        self.assertIn("takes hotfix, stable only", blocked.detail)
        self.assertTrue(allowed.ok)


class ParseTest(unittest.TestCase):
    def test_scopes_table(self):
        scopes = parse_scopes(
            {
                "scopes": [
                    {"name": "dev", "kind": "web", "criticality": "test"},
                    {"name": "nightly", "kind": "job", "criticality": "low"},
                ]
            }
        )

        self.assertEqual([s.name for s in scopes], ["dev", "nightly"])
        self.assertEqual((scopes[1].kind, scopes[1].level), ("job", 1))

    def test_bad_values_are_refused(self):
        for item in (
            {"kind": "web"},
            {"name": "x", "kind": "cron"},
            {"name": "x", "criticality": "urgent"},
        ):
            with self.assertRaises(ConfigError):
                parse_scopes({"scopes": [item]})

    def test_no_scopes_table_means_no_scopes(self):
        self.assertEqual(parse_scopes({"deploy": {"target": "aws/lambda"}}), [])

    def test_config_exposes_scopes(self):
        config = Config.from_dict(
            {
                "deploy": {"target": "aws/lambda"},
                "scopes": [{"name": "prod", "criticality": "high"}],
            }
        )

        self.assertEqual([s.name for s in config.scopes], ["prod"])
        self.assertEqual(config.scope("prod").criticality, "high")

        with self.assertRaises(ConfigError):
            config.scope("qa")
