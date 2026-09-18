"""action_platform.providers.ci.github_actions — the shape of a workflow run."""

from __future__ import annotations

import unittest
from unittest import mock

from action_platform.providers.ci.factory import build_ci_runner, embedded_ci_kind
from action_platform.providers.ci.github_actions import CIGithubActions

RUN = {
    "id": 9001,
    "name": "CI",
    "status": "completed",
    "conclusion": "failure",
    "event": "push",
    "head_branch": "main",
    "head_sha": "def456",
    "html_url": "https://github.com/acme/x/actions/runs/9001",
    "run_started_at": "2026-09-17T10:00:00Z",
    "updated_at": "2026-09-17T10:02:30Z",
}


class GithubActionsTest(unittest.TestCase):
    def setUp(self):
        self.ci = CIGithubActions(repo="acme/x", token="ghp")

    def test_completed_run(self):
        run = CIGithubActions._run(RUN)

        self.assertEqual(run.number, 9001)
        self.assertEqual(run.status, "failure")
        self.assertEqual(run.branch, "main")
        self.assertEqual(run.trigger, "push")
        self.assertEqual(run.duration_ms, 150_000)

    def test_in_progress_has_no_duration(self):
        run = CIGithubActions._run({**RUN, "status": "in_progress", "conclusion": None})

        self.assertEqual(run.status, "running")
        self.assertIsNone(run.duration_ms)

    def test_every_workflow_or_one_file(self):
        with mock.patch(
            "action_platform.providers.ci.github_actions.rest.call"
        ) as call:
            call.return_value = {"workflow_runs": []}
            self.ci.runs("")
            self.ci.runs("ci.yml", limit=5)

        urls = [c.args[1] for c in call.call_args_list]
        self.assertEqual(
            urls[0], "https://api.github.com/repos/acme/x/actions/runs?per_page=50"
        )
        self.assertEqual(
            urls[1],
            "https://api.github.com/repos/acme/x/actions/workflows/ci.yml/runs?per_page=5",
        )


class FactoryTest(unittest.TestCase):
    def test_embedded_kind_of_a_source_host(self):
        self.assertEqual(embedded_ci_kind("github"), "github_actions")
        self.assertEqual(embedded_ci_kind("generic"), "none")
        self.assertEqual(embedded_ci_kind(None), "none")

    def test_build(self):
        self.assertEqual(
            build_ci_runner("jenkins", base_url="https://ci").name, "jenkins"
        )
        self.assertEqual(
            build_ci_runner("github_actions", repo="a/b").name, "github_actions"
        )
        self.assertEqual(build_ci_runner("none").runs("x"), [])
