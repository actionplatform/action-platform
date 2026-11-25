"""action_platform.core.flow.protection — the table, the branches, the checks a CI declares and the patterns."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from action_platform.core.config import Config
from action_platform.core.exception import ConfigError
from action_platform.core.flow.protection import (
    BRANCH_PATTERN,
    COMMIT_PATTERN,
    ProtectionSpec,
    ProtectionState,
    RuleState,
    declared_checks,
    protected_branches,
)

GITHUB_GITFLOW = """name: Git-flow
on:
  pull_request:
    branches: ["main", "master", "develop"]
jobs:
  gitflow:
    name: gitflow
    runs-on: ubuntu-latest
"""
GITHUB_OLD_COMMITS = """name: Conventional commit
on:
  pull_request:
jobs:
  commits:
    runs-on: ubuntu-latest
"""
GITHUB_NAMED = """on: [pull_request]
jobs:
  lint:
    name: conventional-commit
    steps: []
"""


class SpecTest(unittest.TestCase):
    def test_table(self):
        spec = Config.from_dict(
            {"gitflow": {"protection": {"enforce": True, "branches": ["main"]}}}
        ).protection

        self.assertEqual(spec, ProtectionSpec(True, ("main",)))

    def test_absent_follows_the_default(self):
        spec = Config.from_dict({}).protection

        self.assertIsNone(spec.enforce)
        self.assertTrue(spec.resolved(True))
        self.assertFalse(ProtectionSpec(False).resolved(True))

    def test_wrong_types_are_refused(self):
        with self.assertRaises(ConfigError):
            ProtectionSpec.parse({"protection": {"enforce": "yes"}})

        with self.assertRaises(ConfigError):
            ProtectionSpec.parse({"protection": {"branches": "main"}})

    def test_branches_default_to_the_git_flow_ones_present(self):
        self.assertEqual(
            protected_branches(ProtectionSpec(), ["develop", "feature/1", "master"]),
            ("master", "develop"),
        )
        self.assertEqual(
            protected_branches(ProtectionSpec(True, ("trunk",)), ["main"]), ("trunk",)
        )


class DeclaredChecksTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_github_job_names(self):
        self.write(".github/workflows/gitflow.yml", GITHUB_GITFLOW)
        self.write(".github/workflows/conventional-commit.yml", GITHUB_OLD_COMMITS)

        self.assertEqual(declared_checks(self.root, "github"), ("gitflow",))

        self.write(".github/workflows/conventional-commit.yml", GITHUB_NAMED)

        self.assertEqual(
            declared_checks(self.root, "github"), ("gitflow", "conventional-commit")
        )

    def test_gitlab_and_bitbucket(self):
        self.write(
            ".gitlab-ci.yml",
            "gitflow:\n  extends: .ap-gitflow\nconventional-commit:\n  extends: .x\n",
        )
        self.write(
            "bitbucket-pipelines.yml",
            "pipelines:\n  pull-requests:\n    '**':\n      - step:\n          name: gitflow\n",
        )

        self.assertEqual(
            declared_checks(self.root, "gitlab"), ("gitflow", "conventional-commit")
        )
        self.assertEqual(declared_checks(self.root, "bitbucket"), ("gitflow",))
        self.assertEqual(declared_checks(self.root, "jenkins"), ())


class PatternsTest(unittest.TestCase):
    def test_branch_pattern(self):
        ok = [
            "main",
            "develop",
            "feature/42-login",
            "hotfix/PROJ-7",
            "dependabot/npm/x",
        ]
        bad = ["wip", "feature/", "Feature/1", "random/1"]

        for name in ok:
            self.assertRegex(name, BRANCH_PATTERN)

        for name in bad:
            self.assertIsNone(re.match(BRANCH_PATTERN, name), name)

    def test_commit_pattern(self):
        ok = [
            "feat(api): x",
            "fix!: y",
            "Merge pull request #1 from a/b",
            'Revert "feat: x"',
            "chore(release): 1.2.0",
        ]
        bad = ["update stuff", "Feat: x", "feat:x"]

        for message in ok:
            self.assertRegex(message, COMMIT_PATTERN)

        for message in bad:
            self.assertIsNone(re.match(COMMIT_PATTERN, message), message)


class StateTest(unittest.TestCase):
    def test_round_trip(self):
        state = ProtectionState(
            "github", ("main",), ("gitflow",), [RuleState("deletion", "native")]
        )

        again = ProtectionState.from_dict(state.as_dict())

        self.assertEqual(again.as_dict(), state.as_dict())
        self.assertTrue(again.active)
        self.assertEqual(state.as_dict()["rules"][0]["label"], "Deletion blocked")


if __name__ == "__main__":
    unittest.main()
