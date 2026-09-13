"""action_platform.core.flow.gitflow — the rules, and hook installation."""

from __future__ import annotations

import unittest

from action_platform.core.flow import gitflow
from action_platform.core.flow.workflow import GitFlow
from tests.support import TempCase, git, git_repo


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


class AuditOnProtectedTest(TempCase):
    def test_history_before_the_platform_install_is_not_audited(self):
        repo = git_repo(
            self.tmp_path / "legacy", {"README.md": "# x\n"}, "📦 PyPI: 0.1.0"
        )
        git(repo, "tag", "v0.1.0")
        (repo / "README.md").write_text("# y\n")
        git(repo, "commit", "-qam", "📦 PyPI: Update version to 0.2.0")
        git(repo, "checkout", "-qb", "chore/1-configuration", "v0.1.0")
        (repo / "platform.toml").write_text("[project]\nname = 'x'\n")
        git(repo, "add", "platform.toml")
        git(repo, "commit", "-qm", "chore(platform): install")
        git(repo, "checkout", "-q", "main")
        git(
            repo,
            "merge",
            "-q",
            "--no-ff",
            "-m",
            "Merge pull request #1",
            "chore/1-configuration",
        )

        report = GitFlow(repo).audit()

        self.assertEqual(report.problems, [])
        self.assertEqual(report.checked_commits, 1)

        (repo / "README.md").write_text("# z\n")
        git(repo, "commit", "-qam", "bad message")

        self.assertEqual(len(GitFlow(repo).audit().problems), 1)

    def test_without_platform_commit_audits_since_the_last_tag(self):
        repo = git_repo(self.tmp_path / "plain", {"README.md": "# x\n"}, "chore: init")
        git(repo, "tag", "v1.0.0")
        (repo / "README.md").write_text("# y\n")
        git(repo, "commit", "-qam", "feat: y")
        (repo / "README.md").write_text("# z\n")
        git(repo, "commit", "-qam", "nope")

        report = GitFlow(repo).audit()

        self.assertEqual(report.checked_commits, 2)
        self.assertEqual(len(report.problems), 1)
