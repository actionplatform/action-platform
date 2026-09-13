"""action_platform.core.flow.branching — branch naming and base resolution against a throwaway origin."""

from __future__ import annotations

import unittest

from action_platform.core.flow import branching
from action_platform.core.flow.branching import BranchError, branch_name
from tests.support import TempCase, git, repo_with_origin


class BranchNameTest(unittest.TestCase):
    def test_builds_kind_code_slug(self):
        self.assertEqual(branch_name("feature", "42"), "feature/42")
        self.assertEqual(
            branch_name("hotfix", "PROJ-7", "Fix Login!"), "hotfix/PROJ-7-fix-login"
        )
        self.assertEqual(branch_name("release", "1.4.0"), "release/1.4.0")

    def test_rejects_unknown_kind_and_bad_code(self):
        with self.assertRaises(BranchError):
            branch_name("wip", "1")
        with self.assertRaises(BranchError):
            branch_name("feature", "bad code")


class StartBranchTest(TempCase):
    def setUp(self):
        super().setUp()
        self.repo = repo_with_origin(self.tmp_path)

    def test_feature_starts_from_default_when_no_develop(self):
        branch = branching.start("feature", "42", "login", cwd=self.repo)

        self.assertEqual(branch.name, "feature/42-login")
        self.assertEqual(branch.base, "main")
        self.assertEqual(
            git(self.repo, "rev-parse", "--abbrev-ref", "HEAD"), "feature/42-login"
        )
        self.assertIn(
            "feature/42-login", git(self.repo, "ls-remote", "--heads", "origin")
        )

    def test_feature_from_develop_and_hotfix_from_main(self):
        git(self.repo, "checkout", "-qb", "develop")
        git(self.repo, "push", "-q", "-u", "origin", "develop")
        git(self.repo, "checkout", "-q", "main")

        self.assertEqual(
            branching.start("feature", "1", cwd=self.repo, push=False).base, "develop"
        )

        git(self.repo, "checkout", "-q", "main")
        self.assertEqual(
            branching.start("hotfix", "2", cwd=self.repo, push=False).base, "main"
        )

    def test_refuses_dirty_tree_and_duplicates(self):
        branching.start("feature", "9", cwd=self.repo, push=False)
        git(self.repo, "checkout", "-q", "main")

        with self.assertRaisesRegex(BranchError, "already exists"):
            branching.start("feature", "9", cwd=self.repo, push=False)

        (self.repo / "README.md").write_text("dirty\n")

        with self.assertRaisesRegex(BranchError, "dirty"):
            branching.start("feature", "10", cwd=self.repo, push=False)

    def test_default_branch_keeps_slashes(self):
        self.patch(
            branching.git,
            "run",
            lambda args, cwd=None: "refs/remotes/origin/release/1.2",
        )

        self.assertEqual(branching._default_branch(self.tmp_path), "release/1.2")
