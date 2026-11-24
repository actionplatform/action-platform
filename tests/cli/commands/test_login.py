"""action_platform.cli.commands.login — what `login` and `whoami` print."""

from __future__ import annotations

import os
import unittest
from unittest import mock

import typer
from pydantic import ValidationError

from action_platform.cli.commands.login import _describe
from action_platform.remote.credentials import Credentials
from action_platform.remote.schemas import Me


class DescribeTest(unittest.TestCase):
    def test_names_the_reach(self):
        creds = Credentials("https://p.example", "t", "read write")
        who = Me(
            user={"email": "me@example.com"},
            organization={"id": "o1", "name": "Acme"},
            scope=["read", "write"],
            project={"id": "p1", "name": "Shop"},
            app={"id": "a1", "name": "orders", "registry_id": "r1"},
        )

        self.assertEqual(
            _describe(creds, who),
            "me@example.com — scope: read write — on Acme / Shop / orders",
        )
        self.assertEqual(
            _describe(creds, Me(user={"email": "me@example.com"})),
            "me@example.com — scope: read write",
        )
        self.assertEqual(
            _describe(creds, Me(user={}, project={"id": "p1"})),
            "? — scope: read write — on p1",
        )

    def test_a_reach_that_is_not_an_object_is_refused_at_the_boundary(self):
        with self.assertRaises(ValidationError):
            Me.model_validate({"user": {}, "project": "shop"})


class LoginTokenCommandTest(unittest.TestCase):
    def setUp(self):
        from typer.testing import CliRunner

        from action_platform.cli.commands import login as login_cmd

        self.login_cmd = login_cmd
        self.runner = CliRunner()
        self.app = typer.Typer()
        self.app.command("login")(login_cmd.login)
        self.app.command("whoami")(login_cmd.whoami)
        self.seen: list[tuple[str, str]] = []
        test = self

        def fake(server, token):
            test.seen.append((server, token))
            return (
                Credentials(server, token, "read"),
                Me(user={"email": "bot@example.com"}, scope=["read"]),
            )

        patcher = mock.patch.object(login_cmd, "login_with_token", fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_reads_the_token_from_stdin_and_never_prints_it(self):
        with mock.patch.dict(os.environ, {}, clear=False) as env:
            env.pop("AP_TOKEN", None)
            result = self.runner.invoke(
                self.app,
                ["login", "https://p.example", "--token"],
                input="secret.jwt.value\n",
            )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(self.seen, [("https://p.example", "secret.jwt.value")])
        self.assertNotIn("secret.jwt.value", result.output)
        self.assertIn(
            "logged in to https://p.example — bot@example.com — scope: read",
            result.output,
        )

    def test_ap_token_wins_over_stdin_and_an_empty_input_is_refused(self):
        with mock.patch.dict(os.environ, {"AP_TOKEN": "env.jwt.value"}):
            ok = self.runner.invoke(
                self.app, ["login", "https://p.example", "--token"], input=""
            )
        with mock.patch.dict(os.environ, {}, clear=False) as env:
            env.pop("AP_TOKEN", None)
            empty = self.runner.invoke(
                self.app, ["login", "https://p.example", "--token"], input="\n"
            )

        self.assertEqual(ok.exit_code, 0, ok.output)
        self.assertEqual(self.seen, [("https://p.example", "env.jwt.value")])
        self.assertIn("no token", str(empty.exception))
