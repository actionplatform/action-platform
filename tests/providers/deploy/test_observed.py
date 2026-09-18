"""action_platform.providers.deploy — registries asked whether a version is there."""

from __future__ import annotations

import unittest
from unittest import mock

from action_platform.core.context import Context
from action_platform.core.exception import ConfigError, DeployError
from action_platform.providers.deploy import DeployDocker, DeployNpm, DeployPypi


class PypiTest(unittest.TestCase):
    def test_needs_a_package(self):
        with self.assertRaises(ConfigError):
            DeployPypi()

    def test_asks_the_json_api(self):
        target = DeployPypi(package="action-platform")

        with mock.patch.object(DeployPypi, "_exists", return_value=True) as exists:
            self.assertTrue(target.verify("0.18.0"))

        self.assertEqual(
            exists.call_args.args[0],
            "https://pypi.org/pypi/action-platform/0.18.0/json",
        )
        self.assertEqual(
            target.url("0.18.0"), "https://pypi.org/project/action-platform/0.18.0/"
        )

    def test_readiness_refuses_a_version_already_published(self):
        target = DeployPypi(package="action-platform")
        ctx = mock.Mock(spec=Context, next_version="0.18.0", stage="prod")

        with mock.patch.object(DeployPypi, "_exists", return_value=True):
            taken = target.readiness(ctx)

        with mock.patch.object(DeployPypi, "_exists", return_value=False):
            free = target.readiness(ctx)

        self.assertFalse(taken[0].ok)
        self.assertIn("already at", taken[0].detail)
        self.assertTrue(free[0].ok)

    def test_never_deploys(self):
        with self.assertRaises(DeployError):
            DeployPypi(package="x").deploy(mock.Mock(spec=Context))


class NpmTest(unittest.TestCase):
    def test_scoped_package(self):
        target = DeployNpm(package="@acme/sdk")

        with mock.patch.object(DeployNpm, "_exists", return_value=False) as exists:
            self.assertFalse(target.verify("1.0.0"))

        self.assertEqual(
            exists.call_args.args[0], "https://registry.npmjs.org/@acme%2Fsdk/1.0.0"
        )


class DockerTest(unittest.TestCase):
    def test_image_split(self):
        self.assertEqual(
            DeployDocker(image="ghcr.io/actionplatform/api")._split(
                "ghcr.io/actionplatform/api"
            ),
            ("ghcr.io", "actionplatform/api"),
        )
        self.assertEqual(
            DeployDocker._split("nginx"), ("registry-1.docker.io", "library/nginx")
        )
        self.assertEqual(
            DeployDocker._split("acme/app"), ("registry-1.docker.io", "acme/app")
        )
        self.assertEqual(
            DeployDocker._split("localhost:5000/app"), ("localhost:5000", "app")
        )

    def test_urls(self):
        self.assertEqual(
            DeployDocker(image="ghcr.io/actionplatform/api").url("0.21.2"),
            "https://github.com/actionplatform/api/pkgs/container/api",
        )
        self.assertEqual(
            DeployDocker(image="acme/app", tag_prefix="v").url("1.0.0"),
            "https://hub.docker.com/r/acme/app/tags?name=v1.0.0",
        )
