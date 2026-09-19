import unittest

from action_platform.core.config import Config
from action_platform.core.exception import ConfigError
from action_platform.core.scopes import (
    CRITICALITIES,
    accepts,
    derived_scopes,
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
                    {
                        "name": "dev",
                        "kind": "web",
                        "criticality": "test",
                        "target": "aws/lambda",
                        "region": "us-east-1",
                    },
                    {
                        "name": "nightly",
                        "kind": "job",
                        "criticality": "low",
                        "target": "aws/lambda",
                        "run_by": "jenkins",
                    },
                ]
            }
        )

        self.assertEqual([s.name for s in scopes], ["dev", "nightly"])
        self.assertEqual(scopes[0].options, {"region": "us-east-1"})
        self.assertEqual(
            (scopes[1].kind, scopes[1].run_by, scopes[1].level), ("job", "jenkins", 1)
        )

    def test_bad_values_are_refused(self):
        for item in (
            {"kind": "web"},
            {"name": "x", "kind": "cron"},
            {"name": "x", "criticality": "urgent"},
            {"name": "x", "run_by": "me"},
        ):
            with self.assertRaises(ConfigError):
                parse_scopes({"scopes": [item]})

    def test_targets_derive_dev_and_prod(self):
        scopes = derived_scopes({"target": "aws/lambda", "region": "us-east-1"})

        self.assertEqual(
            [(s.name, s.kind, s.criticality, s.target) for s in scopes],
            [
                ("dev", "web", "test", "aws/lambda"),
                ("prod", "web", "high", "aws/lambda"),
            ],
        )
        self.assertEqual(scopes[0].options, {"region": "us-east-1"})

    def test_no_target_still_gives_dev_and_prod(self):
        scopes = derived_scopes({})

        self.assertEqual(
            [(s.name, s.criticality, s.target) for s in scopes],
            [("dev", "test", ""), ("prod", "high", "")],
        )

    def test_observed_targets_derive_library_scopes(self):
        scopes = derived_scopes(
            {
                "targets": [
                    {
                        "name": "pypi",
                        "kind": "pypi",
                        "run_by": "github_actions",
                        "package": "x",
                        "stages": ["release"],
                    }
                ]
            }
        )

        self.assertEqual(
            [(s.name, s.kind, s.criticality, s.run_by) for s in scopes],
            [("pypi", "library", "low", "github_actions")],
        )

    def test_config_exposes_scopes(self):
        config = Config.from_dict({"deploy": {"target": "aws/lambda"}})

        self.assertEqual([s.name for s in config.scopes], ["dev", "prod"])
        self.assertEqual(config.scope("prod").criticality, "high")

        with self.assertRaises(ConfigError):
            config.scope("qa")
