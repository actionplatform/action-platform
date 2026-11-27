"""action_platform.core.targets — what [deploy] declares, and which ref names a release."""

from __future__ import annotations

import unittest

from action_platform.core.config import Config
from action_platform.core.exception import ConfigError
from action_platform.core.targets import TargetSpec, parse_targets, version_from_ref


class ParseTargetsTest(unittest.TestCase):
    def test_short_form_is_one_platform_target_named_after_its_kind(self):
        specs = parse_targets({"target": "aws/lambda", "region": "us-east-1"})

        self.assertEqual(len(specs), 1)
        self.assertEqual(
            (specs[0].name, specs[0].kind, specs[0].run_by),
            ("aws/lambda", "aws/lambda", "platform"),
        )
        self.assertEqual(specs[0].options, {"region": "us-east-1"})

    def test_targets_table_with_executors(self):
        specs = parse_targets(
            {
                "targets": [
                    {"name": "lambda", "kind": "aws/lambda", "stages": ["dev", "prod"]},
                    {
                        "kind": "pypi",
                        "run_by": "github_actions",
                        "workflow": "publish.yml",
                        "package": "x",
                    },
                    {
                        "kind": "docker",
                        "run_by": "jenkins",
                        "job": "team/app",
                        "image": "ghcr.io/a/b",
                    },
                ]
            }
        )

        self.assertEqual([s.name for s in specs], ["lambda", "pypi", "docker"])
        self.assertEqual(specs[0].stages, ("dev", "prod"))
        self.assertTrue(specs[0].platform)
        self.assertEqual(specs[1].workflow, "publish.yml")
        self.assertEqual(specs[2].job, "team/app")
        self.assertFalse(specs[2].platform)

    def test_refusals(self):
        with self.assertRaises(ConfigError):
            parse_targets({"targets": [{"name": "x"}]})

        with self.assertRaises(ConfigError):
            parse_targets({"targets": [{"kind": "pypi", "run_by": "Cron Job"}]})

        with self.assertRaises(ConfigError):
            parse_targets(
                {
                    "targets": [
                        {"kind": "pypi", "name": "a"},
                        {"kind": "npm", "name": "a"},
                    ]
                }
            )

    def test_config_only_runs_platform_targets(self):
        config = Config.from_dict(
            {
                "deploy": {
                    "targets": [
                        {"kind": "pypi", "run_by": "github_actions", "package": "x"}
                    ]
                }
            }
        )

        self.assertEqual(config.deploy, [])
        self.assertEqual(config.target("pypi").name, "pypi")
        self.assertEqual(
            config.target("pypi").url("1.0.0"), "https://pypi.org/project/x/1.0.0/"
        )

    def test_named_target_carries_its_name(self):
        config = Config.from_dict(
            {
                "deploy": {
                    "targets": [
                        {
                            "name": "index",
                            "kind": "pypi",
                            "run_by": "manual",
                            "package": "x",
                        }
                    ]
                }
            }
        )

        self.assertEqual(config.target("index").name, "index")


class ObserveTest(unittest.TestCase):
    def test_observe_turns_a_ci_target_into_an_observed_one(self):
        specs = parse_targets(
            {
                "targets": [
                    {"name": "ci", "kind": "pypi", "run_by": "github_actions"},
                    {
                        "name": "seen",
                        "kind": "pypi",
                        "run_by": "github_actions",
                        "observe": True,
                    },
                    {"name": "jenkins", "kind": "docker", "run_by": "jenkins"},
                    {"name": "hand", "kind": "npm", "run_by": "manual"},
                    {"name": "own", "kind": "aws/lambda"},
                ]
            }
        )

        self.assertEqual(
            [(s.name, s.dispatched, s.observed) for s in specs],
            [
                ("ci", True, False),
                ("seen", False, True),
                ("jenkins", False, True),
                ("hand", False, True),
                ("own", False, False),
            ],
        )
        self.assertNotIn("observe", specs[1].options)

    def test_observe_is_refused_where_it_means_nothing(self):
        with self.assertRaises(ConfigError):
            parse_targets({"targets": [{"kind": "aws/lambda", "observe": True}]})

        with self.assertRaises(ConfigError):
            parse_targets(
                {
                    "targets": [
                        {"kind": "pypi", "run_by": "github_actions", "observe": "yes"}
                    ]
                }
            )

    def test_an_observed_ci_target_is_never_dispatched(self):
        config = Config.from_dict(
            {
                "deploy": {
                    "targets": [
                        {
                            "kind": "pypi",
                            "run_by": "github_actions",
                            "observe": True,
                            "package": "x",
                        }
                    ]
                }
            }
        )

        self.assertEqual(config.dispatched(), [])
        self.assertEqual(config.target("pypi").name, "pypi")


class VersionFromRefTest(unittest.TestCase):
    def test_root_tags(self):
        for ref in ("v1.2.3", "refs/tags/v1.2.3", "tags/v1.2.3", "1.2.3"):
            self.assertEqual(version_from_ref(ref), "1.2.3", ref)

        self.assertEqual(version_from_ref("v0.18.0-rc.1"), "0.18.0-rc.1")

    def test_component_tags(self):
        self.assertEqual(version_from_ref("web/v1.2.3", "web"), "1.2.3")
        self.assertEqual(version_from_ref("refs/tags/api/v0.21.2", "api"), "0.21.2")
        self.assertIsNone(version_from_ref("web/v1.2.3"))
        self.assertIsNone(version_from_ref("v1.2.3", "web"))

    def test_branches_are_not_releases(self):
        for ref in ("main", "feature/226-x", "release/1.2", "", None):
            self.assertIsNone(version_from_ref(ref), ref)


class ObservedRunTest(unittest.TestCase):
    def spec(self, stages=(), **options) -> TargetSpec:
        return TargetSpec("app", "docker", "jenkins", tuple(stages), options)

    def test_the_built_tag_wins(self):
        spec = self.spec(version_parameter="RELEASE_TAG")

        self.assertEqual(spec.run_version("v2.0.0", {"RELEASE_TAG": "v1.0.0"}), "2.0.0")

    def test_version_from_the_parameter_when_the_ref_is_a_branch(self):
        spec = self.spec(version_parameter="RELEASE_TAG")

        for value in ("v1.2.3", "1.2.3", " v1.2.3 "):
            self.assertEqual(spec.run_version("main", {"RELEASE_TAG": value}), "1.2.3")

        self.assertIsNone(spec.run_version("main", {"RELEASE_TAG": "latest"}))
        self.assertIsNone(spec.run_version("main", {}))

    def test_component_parameter(self):
        spec = self.spec(version_parameter="RELEASE_TAG", component="api")

        self.assertEqual(
            spec.run_version("main", {"RELEASE_TAG": "api/v1.2.3"}), "1.2.3"
        )
        self.assertEqual(spec.run_version("main", {"RELEASE_TAG": "v1.2.3"}), "1.2.3")
        self.assertIsNone(spec.run_version("main", {"RELEASE_TAG": "web/v1.2.3"}))

    def test_without_the_option_parameters_are_ignored(self):
        self.assertIsNone(self.spec().run_version("main", {"RELEASE_TAG": "v1.2.3"}))

    def test_stage_from_the_parameter_then_the_only_stage(self):
        self.assertEqual(
            self.spec(["dev", "prod"], stage_parameter="ENV").run_stage(
                {"ENV": "prod"}
            ),
            "prod",
        )
        self.assertEqual(
            self.spec(["prod"], stage_parameter="ENV").run_stage({}), "prod"
        )
        self.assertEqual(self.spec(["prod"]).run_stage({"ENV": "dev"}), "prod")
        self.assertIsNone(self.spec(["dev", "prod"]).run_stage({}))
        self.assertIsNone(self.spec().run_stage({}))


class JenkinsObservesByDefaultTest(unittest.TestCase):
    def test_default_and_explicit(self):
        specs = parse_targets(
            {
                "targets": [
                    {"name": "a", "kind": "docker", "run_by": "jenkins", "job": "x"},
                    {
                        "name": "b",
                        "kind": "docker",
                        "run_by": "jenkins",
                        "job": "x",
                        "observe": False,
                    },
                ]
            }
        )

        self.assertEqual([s.observed for s in specs], [True, False])
        self.assertEqual([s.dispatched for s in specs], [False, True])
