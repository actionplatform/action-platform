"""action_platform.providers.ci.jenkins — job paths, credentials and the shape of a build."""

from __future__ import annotations

import base64
import unittest
from unittest import mock

from action_platform.core.exception import ProviderError
from action_platform.providers.ci.jenkins import CIJenkins

BUILD = {
    "number": 42,
    "result": "SUCCESS",
    "building": False,
    "timestamp": 1_700_000_000_000,
    "duration": 65_000,
    "url": "https://ci.acme.io/job/team/job/app/42/",
    "displayName": "#42",
    "actions": [
        {
            "lastBuiltRevision": {
                "SHA1": "abc123",
                "branch": [{"name": "origin/main"}],
            }
        },
        {"causes": [{"shortDescription": "Started by user ada"}]},
    ],
}


class JenkinsTest(unittest.TestCase):
    def setUp(self):
        self.ci = CIJenkins(base_url="https://ci.acme.io/", token="tok", username="ada")

    def test_basic_auth_header(self):
        raw = base64.b64encode(b"ada:tok").decode()

        self.assertEqual(self.ci._headers(), {"authorization": f"Basic {raw}"})

    def test_folders_become_job_segments(self):
        self.assertEqual(
            self.ci._job_url("team/app/main"),
            "https://ci.acme.io/job/team/job/app/job/main",
        )

    def test_empty_job_is_refused(self):
        with self.assertRaises(ProviderError):
            self.ci._job_url("/")

    def test_build_becomes_a_run(self):
        run = CIJenkins._run(BUILD)

        self.assertEqual(run.number, 42)
        self.assertEqual(run.status, "success")
        self.assertEqual(run.branch, "main")
        self.assertEqual(run.sha, "abc123")
        self.assertEqual(run.trigger, "Started by user ada")
        self.assertEqual(run.duration_ms, 65_000)
        self.assertEqual(run.started_at.year, 2023)

    def test_building_wins_over_result(self):
        run = CIJenkins._run({**BUILD, "building": True, "result": None})

        self.assertEqual(run.status, "running")

    def test_unknown_result(self):
        run = CIJenkins._run({"number": 1, "result": "WEIRD"})

        self.assertEqual(run.status, "unknown")
        self.assertIsNone(run.branch)

    def test_runs_calls_the_job_api_with_the_tree(self):
        with mock.patch("action_platform.providers.ci.jenkins.rest.call") as call:
            call.return_value = {"builds": [BUILD]}
            runs = self.ci.runs("team/app", limit=10)

        self.assertEqual([r.number for r in runs], [42])
        url = call.call_args.args[1]
        self.assertTrue(
            url.startswith("https://ci.acme.io/job/team/job/app/api/json?tree=builds[")
        )
        self.assertTrue(url.endswith("{0,10}"))
