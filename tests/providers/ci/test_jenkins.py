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
        self.assertEqual(run.params, {})

    def test_parameters_become_run_params(self):
        build = {
            **BUILD,
            "actions": [
                *BUILD["actions"],
                {
                    "_class": "hudson.model.ParametersAction",
                    "parameters": [
                        {"name": "RELEASE_TAG", "value": "v1.4.0"},
                        {"name": "DRY_RUN", "value": False},
                        {"name": "EMPTY", "value": None},
                    ],
                },
            ],
        }

        run = CIJenkins._run(build)

        self.assertEqual(run.params, {"RELEASE_TAG": "v1.4.0", "DRY_RUN": "False"})

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
        self.assertIn("parameters[name,value]", url)


class FollowTest(unittest.TestCase):
    def setUp(self):
        self.ci = CIJenkins(base_url="https://ci.acme.io", token="tok", username="ada")

    def test_start_without_a_ref_sends_only_the_parameters(self):
        with (
            mock.patch(
                "action_platform.providers.ci.jenkins.rest.call", return_value={}
            ),
            mock.patch(
                "action_platform.providers.ci.jenkins.rest.location",
                return_value="https://ci.acme.io/queue/item/12/",
            ) as post,
        ):
            ref = self.ci.start("team/app", "", {"RELEASE_TAG": "v1.2.3"})

        self.assertEqual(
            post.call_args.args[1],
            "https://ci.acme.io/job/team/job/app/buildWithParameters?RELEASE_TAG=v1.2.3",
        )
        self.assertEqual(ref.id, "queue:12")

    def test_a_waiting_item_has_no_run_then_the_build_is_read(self):
        from action_platform.core.context import RunRef

        ref = RunRef(id="queue:12")

        with mock.patch(
            "action_platform.providers.ci.jenkins.rest.call",
            side_effect=[
                {"why": "waiting"},
                {"executable": {"number": 42}},
                BUILD,
                BUILD,
            ],
        ) as call:
            self.assertIsNone(self.ci.run_of("team/app", ref))
            self.assertEqual(self.ci.run_of("team/app", ref).number, 42)
            self.assertEqual(self.ci.run_of("team/app", ref).number, 42)

        urls = [c.args[1] for c in call.call_args_list]
        self.assertEqual(urls.count("https://ci.acme.io/queue/item/12/api/json"), 2)

    def test_a_cancelled_item_is_refused(self):
        from action_platform.core.context import RunRef
        from action_platform.core.exception import DeployError

        with mock.patch(
            "action_platform.providers.ci.jenkins.rest.call",
            return_value={"cancelled": True},
        ):
            with self.assertRaises(DeployError):
                self.ci.run_of("team/app", RunRef(id="queue:3"))

    def test_a_ref_without_a_queue_item_is_looked_for_elsewhere(self):
        from action_platform.core.context import RunRef

        with self.assertRaises(NotImplementedError):
            self.ci.run_of("team/app", RunRef(id="team/app@v1"))

    def test_stages_come_from_the_pipeline_description(self):
        with mock.patch(
            "action_platform.providers.ci.jenkins.rest.call",
            return_value={
                "stages": [
                    {"name": "Migrate", "status": "SUCCESS"},
                    {"name": "Deploy", "status": "IN_PROGRESS"},
                ]
            },
        ) as call:
            stages = self.ci.stages("team/app", 42)

        self.assertEqual(stages, [("Migrate", "SUCCESS"), ("Deploy", "IN_PROGRESS")])
        self.assertEqual(
            call.call_args.args[1],
            "https://ci.acme.io/job/team/job/app/42/wfapi/describe",
        )
