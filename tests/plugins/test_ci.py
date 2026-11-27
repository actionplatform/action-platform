from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from typer.testing import CliRunner

from action_platform.abc.ci_runner import CIRunner, LogChunk, QueueItem
from action_platform.cli.commands import ci as ci_cmd
from action_platform.core.context import Cause, Change, Run
from action_platform.core.exception import ConfigError, ProviderError
from action_platform.plugins import ci
from action_platform.plugins.options import FileOptions
from tests.mcp.support import HAS_MCP, McpCase

STARTED = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


class Server(CIRunner):
    name = "acme_ci"

    def __init__(self, base_url, token=None, username=None):
        self.base_url, self.token, self.username = base_url, token, username
        self.chunks = [LogChunk("one\n", 4, True), LogChunk("two\n", 8, False)]

    def runs(self, job, limit=50):
        return [self.run(job, 7), self.run(job, 6)][:limit]

    def run(self, job, number):
        return Run(
            number=number,
            status="success",
            branch="main",
            started_at=STARTED,
            params={"REF": "v1.0.0"},
            causes=[Cause("Started by user ana", "ana")],
            changes=[Change("abc1234", "ana", "feat: x")],
        )

    def log(self, job, number, start=0, node=None):
        return next(c for c in self.chunks if c.next_start > start)

    def queue(self):
        return [QueueItem("team/app", STARTED, "Waiting for next available executor")]


def plugged():
    return mock.patch(
        "action_platform.core.module.load_ci_runners",
        return_value={"acme_ci": Server},
    )


ENV = {"AP_ACME_CI_URL": "https://ci.example.com", "AP_ACME_CI_TOKEN": "t0k"}


class Runner(unittest.TestCase):
    def setUp(self):
        patch = plugged()
        patch.start()
        self.addCleanup(patch.stop)
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_the_only_server_installed_is_the_default(self):
        with mock.patch.dict("os.environ", ENV):
            runner = ci.runner()

        self.assertIsInstance(runner, Server)
        self.assertEqual(
            (runner.base_url, runner.token), ("https://ci.example.com", "t0k")
        )

    def test_the_plugin_options_are_the_fallback(self):
        options = FileOptions("acme_ci", Path(self.tmp.name))
        options.set("url", "https://from-options")
        options.set("user", "ana")

        with mock.patch.dict("os.environ", {}, clear=True):
            runner = ci.runner("acme_ci", options)

        self.assertEqual(
            (runner.base_url, runner.username), ("https://from-options", "ana")
        )

    def test_without_a_url_the_setting_is_named(self):
        options = FileOptions("acme_ci", Path(self.tmp.name))

        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ConfigError, "AP_ACME_CI_URL"):
                ci.runner("acme_ci", options)

    def test_no_server_installed_says_so(self):
        with mock.patch("action_platform.core.module.load_ci_runners", return_value={}):
            with self.assertRaisesRegex(ConfigError, "none is installed"):
                ci.runner()


class Answers(unittest.TestCase):
    def setUp(self):
        self.ci = Server("https://ci")

    def test_a_run_carries_parameters_causes_and_changes(self):
        run = ci.run(self.ci, "team/app", 7)

        self.assertEqual(run["parameters"], {"REF": "v1.0.0"})
        self.assertEqual(
            run["causes"], [{"description": "Started by user ana", "user": "ana"}]
        )
        self.assertEqual(run["changes"][0]["sha"], "abc1234")
        self.assertEqual(run["started_at"], STARTED.isoformat())

    def test_number_zero_is_the_latest(self):
        self.assertEqual(ci.run(self.ci, "team/app", 0)["number"], 7)

    def test_runs_log_and_queue(self):
        self.assertEqual([r["number"] for r in ci.runs(self.ci, "team/app", 1)], [7])
        self.assertEqual(
            ci.log(self.ci, "team/app", 7, 4),
            {"text": "two\n", "next_start": 8, "more": False},
        )
        self.assertEqual(ci.queue(self.ci)[0]["job"], "team/app")

    def test_what_the_ci_cannot_answer_is_a_provider_error(self):
        with self.assertRaisesRegex(ProviderError, "cannot list executors"):
            ci._ask(self.ci.executors)


class Commands(unittest.TestCase):
    def setUp(self):
        for patch in (plugged(), mock.patch.dict("os.environ", ENV)):
            patch.start()
            self.addCleanup(patch.stop)

    def test_run_prints_json(self):
        out = CliRunner().invoke(ci_cmd.app, ["run", "team/app", "7"])

        self.assertEqual(out.exit_code, 0, out.output)
        self.assertEqual(json.loads(out.output)["causes"][0]["user"], "ana")

    def test_log_follows_until_the_run_ends(self):
        with mock.patch.object(ci_cmd, "FOLLOW_SECONDS", 0):
            out = CliRunner().invoke(ci_cmd.app, ["log", "team/app", "7", "--follow"])

        self.assertEqual((out.exit_code, out.output), (0, "one\ntwo\n"))

    def test_queue(self):
        out = CliRunner().invoke(ci_cmd.app, ["queue"])

        self.assertEqual(
            json.loads(out.output)[0]["why"], "Waiting for next available executor"
        )


@unittest.skipUnless(HAS_MCP, "mcp is not installed")
class Tools(McpCase):
    def setUp(self):
        for patch in (plugged(), mock.patch.dict("os.environ", ENV)):
            patch.start()
            self.addCleanup(patch.stop)
        super().setUp()

    def test_the_tools_are_read_only(self):
        tools = self.tools()

        for name in ("ci_runs", "ci_run", "ci_log", "ci_queue"):
            self.assertTrue(tools[name].annotations.read_only_hint, name)

    def test_the_tools_answer_the_contract(self):
        self.assertEqual(
            self.call("ci_run", job="team/app", number=7)["status"], "success"
        )
        self.assertEqual(len(self.call("ci_runs", job="team/app")), 2)
        self.assertTrue(self.call("ci_log", job="team/app", number=7)["more"])
        self.assertEqual(self.call("ci_queue")[0]["job"], "team/app")
