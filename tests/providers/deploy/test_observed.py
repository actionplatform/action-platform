"""action_platform.providers.deploy — registries asked whether a version is there."""

from __future__ import annotations

import unittest
import io
import urllib.error
from unittest import mock

from action_platform.core.context import Context
from action_platform.core.exception import ConfigError, DeployError, ProviderError
from action_platform.core.config import Config
from action_platform.providers.deploy import (
    DeployDocker,
    DeployGo,
    DeployNpm,
    DeployPackagist,
    DeployPypi,
)
from action_platform.providers.deploy.pipeline_published import (
    PipelinePublishedTarget,
)


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
        ctx = mock.Mock(
            spec=Context, next_version="0.18.0", stage="prod", observed=False
        )

        with mock.patch.object(DeployPypi, "_exists", return_value=True):
            taken = target.readiness(ctx)

        with mock.patch.object(DeployPypi, "_exists", return_value=False):
            free = target.readiness(ctx)

        self.assertFalse(taken[0].ok)
        self.assertIn("already at", taken[0].detail)
        self.assertTrue(free[0].ok)

    def test_readiness_of_an_observed_target_expects_the_version_there(self):
        target = DeployPypi(package="action-platform")
        ctx = mock.Mock(
            spec=Context, next_version="0.18.0", stage="prod", observed=True
        )

        with mock.patch.object(DeployPypi, "_exists", return_value=True):
            there = target.readiness(ctx)

        self.assertTrue(there[0].ok)
        self.assertIn("already at", there[0].detail)
        self.assertIsNone(there[0].fix)

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


PACKAGIST = {
    "packages": {
        "acme/sdk": [
            {"version": "v1.2.0", "version_normalized": "1.2.0.0"},
            {"version": "1.1.0", "version_normalized": "1.1.0.0"},
        ]
    },
    "minified": "composer/2.0",
}


class PackagistTest(unittest.TestCase):
    def test_needs_vendor_and_name(self):
        for package in ("", "sdk"):
            with self.assertRaises(ConfigError):
                DeployPackagist(package=package)

    def test_reads_the_listed_versions(self):
        target = DeployPackagist(package="Acme/SDK")

        with mock.patch.object(
            DeployPackagist, "_json", return_value=PACKAGIST
        ) as fetched:
            self.assertTrue(target.verify("1.2.0"))
            self.assertTrue(target.verify("1.1.0"))
            self.assertFalse(target.verify("1.3.0"))

        self.assertEqual(
            fetched.call_args.args[0], "https://repo.packagist.org/p2/acme/sdk.json"
        )
        self.assertEqual(target.url("1.2.0"), "https://packagist.org/packages/acme/sdk")

    def test_an_unknown_package_is_not_there(self):
        with mock.patch.object(DeployPackagist, "_json", return_value=None):
            self.assertFalse(DeployPackagist(package="acme/sdk").verify("1.0.0"))

    def test_readiness_refuses_a_version_already_published(self):
        ctx = mock.Mock(
            spec=Context, next_version="1.2.0", stage="prod", observed=False
        )

        with mock.patch.object(DeployPackagist, "_json", return_value=PACKAGIST):
            taken = DeployPackagist(package="acme/sdk").readiness(ctx)
            ctx.next_version = "1.3.0"
            free = DeployPackagist(package="acme/sdk").readiness(ctx)

        self.assertFalse(taken[0].ok)
        self.assertTrue(free[0].ok)


class GoTest(unittest.TestCase):
    def test_needs_a_module(self):
        with self.assertRaises(ConfigError):
            DeployGo()

    def test_asks_the_proxy_with_capitals_escaped(self):
        target = DeployGo(module="github.com/Acme/SDK/v2")

        with mock.patch.object(DeployGo, "_exists", return_value=True) as exists:
            self.assertTrue(target.verify("2.1.0"))

        self.assertEqual(
            exists.call_args.args[0],
            "https://proxy.golang.org/github.com/!acme/!s!d!k/v2/@v/v2.1.0.info",
        )
        self.assertEqual(
            target.url("2.1.0"), "https://pkg.go.dev/github.com/Acme/SDK/v2@v2.1.0"
        )

    def test_readiness_refuses_a_version_already_published(self):
        ctx = mock.Mock(
            spec=Context, next_version="1.0.0", stage="prod", observed=False
        )

        with mock.patch.object(DeployGo, "_exists", return_value=True):
            taken = DeployGo(module="github.com/acme/sdk").readiness(ctx)

        self.assertFalse(taken[0].ok)
        self.assertIn("already at https://pkg.go.dev/", taken[0].detail)


class BuiltinKindsTest(unittest.TestCase):
    def test_resolve_without_a_plugin(self):
        config = Config.from_dict(
            {
                "deploy": {
                    "targets": [
                        {"kind": "packagist", "run_by": "manual", "package": "a/b"},
                        {"kind": "go", "run_by": "manual", "module": "example.com/m"},
                    ]
                }
            }
        )

        self.assertIsInstance(config.target("packagist"), DeployPackagist)
        self.assertIsInstance(config.target("go"), DeployGo)


class JsonFetchTest(unittest.TestCase):
    def response(self, body: bytes):
        res = mock.MagicMock()
        res.__enter__.return_value.read.return_value = body

        return res

    def test_parses_the_document(self):
        with mock.patch(
            "urllib.request.urlopen", return_value=self.response(b'{"a": 1}')
        ):
            self.assertEqual(
                PipelinePublishedTarget._json("https://x/y.json"), {"a": 1}
            )

    def test_not_found_is_none_and_other_errors_raise(self):
        def fail(code):
            return urllib.error.HTTPError("https://x", code, "x", {}, io.BytesIO())

        with mock.patch("urllib.request.urlopen", side_effect=fail(404)):
            self.assertIsNone(PipelinePublishedTarget._json("https://x/y.json"))

        with mock.patch("urllib.request.urlopen", side_effect=fail(500)):
            with self.assertRaises(ProviderError):
                PipelinePublishedTarget._json("https://x/y.json")

        with mock.patch(
            "urllib.request.urlopen", return_value=self.response(b"<html>")
        ):
            with self.assertRaises(ProviderError):
                PipelinePublishedTarget._json("https://x/y.json")
