"""action_platform.providers.ci — GitLab CI and Bitbucket Pipelines in the platform's shape, and starting a run on every runner."""

from __future__ import annotations

import unittest
from unittest import mock

from action_platform.providers.ci.bitbucket_pipelines import CIBitbucket
from action_platform.providers.ci.factory import build_ci_runner, embedded_ci_kind
from action_platform.providers.ci.github_actions import CIGithubActions
from action_platform.providers.ci.gitlab_ci import CIGitlab
from action_platform.providers.ci.jenkins import CIJenkins


class GitlabTest(unittest.TestCase):
    def test_pipeline_becomes_a_run(self):
        run = CIGitlab._run(
            {
                "id": 501,
                "iid": 12,
                "status": "failed",
                "ref": "main",
                "sha": "abc",
                "web_url": "https://gl/p/501",
                "source": "push",
                "created_at": "2026-09-18T10:00:00Z",
                "started_at": "2026-09-18T10:00:10Z",
                "updated_at": "2026-09-18T10:03:10Z",
            }
        )

        self.assertEqual(
            (run.number, run.name, run.status, run.branch, run.duration_ms),
            (501, "#12", "failure", "main", 180_000),
        )

    def test_start_posts_a_pipeline(self):
        ci = CIGitlab(repo="acme/x", token="glpat", base_url="https://git.acme.io")

        with mock.patch(
            "action_platform.providers.ci.gitlab_ci.rest.call",
            return_value={
                "id": 9,
                "web_url": "https://git.acme.io/acme/x/-/pipelines/9",
            },
        ) as call:
            ref = ci.start("", "main", {"DEPLOY": "1"})

        self.assertEqual(ref.id, "9")
        self.assertEqual(
            call.call_args.args[:2],
            ("POST", "https://git.acme.io/api/v4/projects/acme%2Fx/pipeline"),
        )
        self.assertEqual(
            call.call_args.args[3]["variables"], [{"key": "DEPLOY", "value": "1"}]
        )


class BitbucketTest(unittest.TestCase):
    def test_pipeline_becomes_a_run(self):
        ci = CIBitbucket(repo="acme/x", token="t", username="ada")
        run = ci._run(
            {
                "build_number": 33,
                "state": {"name": "COMPLETED", "result": {"name": "SUCCESSFUL"}},
                "target": {"ref_name": "develop", "commit": {"hash": "deadbeef"}},
                "trigger": {"name": "PUSH"},
                "created_on": "2026-09-18T10:00:00Z",
                "duration_in_seconds": 42,
            }
        )

        self.assertEqual(
            (run.number, run.status, run.branch, run.sha, run.duration_ms),
            (33, "success", "develop", "deadbeef", 42_000),
        )
        self.assertEqual(run.url, "https://bitbucket.org/acme/x/pipelines/results/33")

    def test_in_progress(self):
        run = CIBitbucket(repo="a/b")._run(
            {"build_number": 1, "state": {"name": "IN_PROGRESS"}, "target": {}}
        )

        self.assertEqual(run.status, "running")


class StartTest(unittest.TestCase):
    def test_github_dispatches_a_workflow(self):
        ci = CIGithubActions(repo="acme/x", token="ghp")

        with mock.patch(
            "action_platform.providers.ci.github_actions.rest.call", return_value=None
        ) as call:
            ref = ci.start("ci.yml", "main")

        self.assertEqual(
            call.call_args.args[1],
            "https://api.github.com/repos/acme/x/actions/workflows/ci.yml/dispatches",
        )
        self.assertEqual(call.call_args.args[3], {"ref": "main", "inputs": {}})
        self.assertEqual(ref.url, "https://github.com/acme/x/actions/workflows/ci.yml")

    def test_jenkins_builds_with_the_crumb(self):
        ci = CIJenkins(base_url="https://ci.acme.io", token="t", username="u")

        with mock.patch(
            "action_platform.providers.ci.jenkins.rest.call",
            side_effect=[{"crumbRequestField": "Jenkins-Crumb", "crumb": "c1"}, None],
        ) as call:
            ci.start("team/app", "main")

        post = call.call_args_list[1]
        self.assertEqual(post.args[0], "POST")
        self.assertTrue(
            post.args[1].startswith(
                "https://ci.acme.io/job/team/job/app/buildWithParameters?REF=main"
            )
        )
        self.assertEqual(post.args[2]["Jenkins-Crumb"], "c1")


class FactoryTest(unittest.TestCase):
    def test_embedded_kinds(self):
        self.assertEqual(embedded_ci_kind("gitlab"), "gitlab_ci")
        self.assertEqual(embedded_ci_kind("bitbucket"), "bitbucket_pipelines")
        self.assertEqual(build_ci_runner("gitlab_ci", repo="a/b").name, "gitlab_ci")
        self.assertEqual(
            build_ci_runner("bitbucket_pipelines", repo="a/b").name,
            "bitbucket_pipelines",
        )
