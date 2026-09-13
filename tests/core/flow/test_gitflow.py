"""action_platform.core.flow.gitflow — the rules, and hook installation."""

from __future__ import annotations

import unittest

from action_platform.core.flow import gitflow


class RulesTest(unittest.TestCase):
    def test_branch_names(self):
        self.assertIsNone(gitflow.check_branch("feature/42-login"))
        self.assertIsNone(gitflow.check_branch("main"))
        self.assertIsNotNone(gitflow.check_branch("wip"))
        self.assertIsNotNone(gitflow.check_branch("fix/1"))

    def test_commit_messages(self):
        self.assertIsNone(gitflow.check_commit("feat(api): x"))
        self.assertIsNone(gitflow.check_commit("Merge branch 'x'"))
        self.assertIsNotNone(gitflow.check_commit("update stuff"))
        self.assertIsNotNone(gitflow.check_commit("Feat: caps"))

    def test_protected_branches(self):
        self.assertIsNone(gitflow.check_protected("feature/1", "feat: x"))
        self.assertIsNone(gitflow.check_protected("main", "chore(release): 1.0.0"))
        self.assertIsNone(
            gitflow.check_protected(
                "main", "chore: bootstrap project from action-platform"
            )
        )
        self.assertIsNotNone(gitflow.check_protected("main", "feat: x"))
        self.assertIsNotNone(gitflow.check_protected("develop", "fix: y"))

    def test_targets(self):
        self.assertIsNone(gitflow.check_target("feature/1", "develop", "main", True))
        self.assertIsNone(gitflow.check_target("feature/1", "main", "main", False))
        self.assertIsNotNone(gitflow.check_target("feature/1", "main", "main", True))
        self.assertIsNone(gitflow.check_target("hotfix/1", "main", "main", True))
        self.assertIsNone(gitflow.check_target("hotfix/1", "develop", "main", True))
        self.assertIsNone(gitflow.check_target("release/1.0", "main", "main", True))
        self.assertIsNone(gitflow.check_target("develop", "main", "main", True))
        self.assertIsNotNone(gitflow.check_target("main", "develop", "main", True))
        self.assertIsNotNone(gitflow.check_target("support/1", "main", "main", True))
