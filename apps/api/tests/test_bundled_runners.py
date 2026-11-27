"""The CI runners the API image bundles, resolved through the action_platform.ci_runner entry point as a deploy or Run CI resolves them."""

from __future__ import annotations

import unittest

from action_platform.abc.ci_runner import CIRunner
from action_platform.providers.ci import build_ci_runner, ci_kinds


class BundledRunnersTest(unittest.TestCase):
    def test_jenkins_comes_from_apx_jenkins(self):
        runner = build_ci_runner(
            "jenkins",
            base_url="https://jenkins.example.com",
            username="ana",
            token="t0k",
        )

        self.assertIsInstance(runner, CIRunner)
        self.assertEqual(runner.name, "jenkins")
        self.assertEqual(type(runner).__module__.split(".")[0], "apx_jenkins")
        self.assertIn("jenkins", ci_kinds())
