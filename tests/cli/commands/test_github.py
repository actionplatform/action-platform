from __future__ import annotations

import json

from typer.testing import CliRunner

from action_platform.cli.commands import github
from action_platform.providers.access.github import Org
from action_platform.remote import client
from action_platform.testing.github import FakeGitHub
from tests.support import TempCase


class Checks:
    def __init__(self, org: Org) -> None:
        self.org = org
        self.calls: list[tuple] = []

    def github_branch_protection(self, repo=None, organization=None):
        self.calls.append(("branch-protection", repo, organization))

        return self.org.branch_protection(repo)

    def github_repo_settings(self, repo=None, organization=None):
        self.calls.append(("repo-settings", repo, organization))

        return self.org.repo_settings(repo)


class GitHubCommandsTest(TempCase):
    def test_commands_print_the_models_as_json(self):
        fake = FakeGitHub()
        fake.repo("api")
        checks = Checks(Org(fake, "acme"))
        self.patch(client.Remote, "from_credentials", classmethod(lambda cls: checks))
        runner = CliRunner()

        protection = runner.invoke(github.app, ["branch-protection", "--repo", "api"])
        settings = runner.invoke(
            github.app, ["repo-settings", "--organization", "acme"]
        )

        self.assertEqual(json.loads(protection.output)["repos"][0]["repo"], "api")
        self.assertEqual(
            json.loads(settings.output)["repos"][0]["visibility"], "public"
        )
        self.assertEqual(
            checks.calls,
            [("branch-protection", "api", None), ("repo-settings", None, "acme")],
        )
