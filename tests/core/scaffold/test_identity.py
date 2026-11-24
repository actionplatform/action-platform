"""action_platform.core.scaffold.identity — owner, author, licence and host of a generated project."""

from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from action_platform.core.exception import ProviderError, TemplateError
from action_platform.core.scaffold import identity
from action_platform.options import SourceTokens


def ran(stdout: str, code: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], code, stdout=stdout, stderr="")


class HostAndLicenceTest(unittest.TestCase):
    def test_the_host_follows_a_hosted_ci(self):
        self.assertEqual(identity.host_for("gitlab"), "gitlab")
        self.assertEqual(identity.host_for("bitbucket"), "bitbucket")
        self.assertEqual(identity.host_for("jenkins"), "github")
        self.assertEqual(identity.host_for(None), "github")

    def test_unknown_values_are_refused(self):
        identity.check("apache-2.0", "gitlab")

        with self.assertRaisesRegex(TemplateError, "unknown license: gpl"):
            identity.check("gpl", "github")

        with self.assertRaisesRegex(TemplateError, "unknown host: gitea"):
            identity.check("none", "gitea")


class AccountTest(unittest.TestCase):
    def test_a_github_token_answers_its_login(self):
        with mock.patch.object(
            identity.rest, "call", return_value={"login": "alice"}
        ) as call:
            found = identity.account("github", SourceTokens(github="t"))

        self.assertEqual(found, "alice")
        self.assertEqual(call.call_args.args[1], "https://api.github.com/user")

    def test_without_a_token_the_gh_cli_answers(self):
        with (
            mock.patch.object(identity.shutil, "which", return_value="/bin/gh"),
            mock.patch.object(identity.subprocess, "run", return_value=ran("bob\n")),
        ):
            self.assertEqual(identity.account("github", SourceTokens()), "bob")

    def test_nothing_known_is_empty_never_a_default(self):
        with mock.patch.object(identity.shutil, "which", return_value=None):
            self.assertEqual(identity.account("github", SourceTokens()), "")

        with mock.patch.object(identity.rest, "call", side_effect=ProviderError("401")):
            self.assertEqual(identity.account("gitlab", SourceTokens(gitlab="t")), "")

        self.assertEqual(
            identity.account("bitbucket", SourceTokens(bitbucket_username="carol")),
            "carol",
        )


class GitAuthorTest(unittest.TestCase):
    def test_git_config_user_name_or_empty(self):
        with mock.patch.object(
            identity.subprocess, "run", return_value=ran("Ana Lima\n")
        ):
            self.assertEqual(identity.git_author(), "Ana Lima")

        with mock.patch.object(identity.subprocess, "run", return_value=ran("", 1)):
            self.assertEqual(identity.git_author(), "")
