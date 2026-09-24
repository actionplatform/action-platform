"""action_platform.providers.registry — source hosts and CI runners built by kind from one registry each."""

from __future__ import annotations

import unittest

from action_platform.core.exception import ConfigError, ProviderError
from action_platform.providers.ci.factory import CI_KINDS, CI_RUNNERS, build_ci_runner
from action_platform.providers.registry import ProviderRegistry
from action_platform.providers.source.factory import (
    SOURCE_HOST_KINDS,
    build_source_host,
)


class Plain:
    name = "plain"

    def __init__(self, repo: str, token: str | None = None) -> None:
        self.repo = repo
        self.token = token


class RegistryTest(unittest.TestCase):
    def test_a_class_gets_only_the_arguments_it_takes(self):
        registry: ProviderRegistry[Plain] = ProviderRegistry("thing")
        registry.register(Plain, "alias")

        built = registry.build("alias", repo="a/b", token="t", username="ada")

        self.assertEqual((built.repo, built.token), ("a/b", "t"))
        self.assertEqual(registry.kinds(), ("plain",))

    def test_an_unknown_kind_names_the_available_ones(self):
        registry: ProviderRegistry[Plain] = ProviderRegistry("thing")
        registry.register(Plain)

        with self.assertRaises(ConfigError) as raised:
            registry.build("nope")

        self.assertEqual(
            str(raised.exception), "unknown thing kind: nope (available: plain)"
        )


class SourceFactoryTest(unittest.TestCase):
    def test_kinds_and_aliases(self):
        self.assertEqual(
            SOURCE_HOST_KINDS, ("github", "gitlab", "bitbucket", "generic")
        )
        self.assertEqual(build_source_host("other", "a/b").name, "generic")

        for kind in SOURCE_HOST_KINDS:
            host = build_source_host(kind, "a/b", token="t", username="ada")

            self.assertEqual((host.name, host.repo), (kind, "a/b"))

    def test_username_reaches_the_hosts_that_take_one(self):
        host = build_source_host("bitbucket", "a/b", token="t", username="ada")

        self.assertEqual(host.username, "ada")

    def test_an_unknown_kind_is_a_config_error(self):
        with self.assertRaises(ConfigError) as raised:
            build_source_host("svn", "a/b")

        self.assertIn("unknown source_host kind: svn", str(raised.exception))


class CiFactoryTest(unittest.TestCase):
    def test_kinds_and_the_empty_kind(self):
        self.assertEqual(
            CI_KINDS,
            ("github_actions", "gitlab_ci", "bitbucket_pipelines", "jenkins", "none"),
        )
        self.assertEqual(build_ci_runner("").name, "none")
        self.assertEqual(build_ci_runner(None).name, "none")

    def test_servers_take_their_own_url(self):
        runner = build_ci_runner("jenkins", base_url="https://ci/", username="ada")

        self.assertEqual((runner.base_url, runner.username), ("https://ci", "ada"))

        with self.assertRaises(ProviderError):
            build_ci_runner("jenkins")

    def test_a_new_runner_registers_without_editing_the_factory(self):
        class Custom(Plain):
            name = "custom_ci"

        CI_RUNNERS.register(Custom)
        self.addCleanup(CI_RUNNERS.classes.pop, "custom_ci")
        self.addCleanup(CI_RUNNERS.primary.remove, "custom_ci")

        self.assertIsInstance(build_ci_runner("custom_ci", repo="a/b"), Custom)

    def test_an_unknown_kind_is_a_config_error(self):
        with self.assertRaises(ConfigError) as raised:
            build_ci_runner("travis")

        self.assertIn("unknown ci kind: travis", str(raised.exception))
