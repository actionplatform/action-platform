"""action_platform.core.flow.repo — each command group works on its own, and Repository still carries them all."""

from __future__ import annotations

import unittest
from pathlib import Path

from action_platform.abc.working_copy import WorkingCopy
from action_platform.core.flow.repo.branches import Branches
from action_platform.core.flow.repo.history import History
from action_platform.core.flow.repo.remotes import Remotes
from action_platform.core.flow.repo.sync import Sync
from action_platform.core.flow.repo.tags import Tags
from action_platform.core.flow.repository import Repository
from tests.core.flow.test_repository import FakeGit


def bound(group, answers=None):
    obj = group()
    obj.path = Path("/work")
    obj.runner = FakeGit(answers)

    return obj


class GroupsTest(unittest.TestCase):
    def test_tags_alone(self):
        tags = bound(Tags, {("tag", "--list", "--sort=v:refname"): (0, "v1\nv2\n", "")})

        self.assertEqual(tags.tags(), ["v1", "v2"])
        tags.tag("v3")
        self.assertEqual(tags.runner.calls[-1][0], ["tag", "-a", "v3", "-m", "v3"])

    def test_history_alone(self):
        history = bound(History, {("status", "--porcelain"): (0, "", "")})

        self.assertTrue(history.is_clean())
        history.commit("feat: x")
        self.assertEqual(
            history.runner.calls[-1][0], ["commit", "-m", "feat: x", "--end-of-options"]
        )

    def test_remotes_alone(self):
        remotes = bound(Remotes)
        remotes.push_upstream("feature/1")

        self.assertEqual(
            remotes.runner.calls[-1][0],
            ["push", "-u", "--end-of-options", "origin", "feature/1"],
        )

    def test_repository_is_every_group_and_a_working_copy(self):
        for group in (Branches, History, Remotes, Sync, Tags, WorkingCopy):
            self.assertTrue(issubclass(Repository, group))

        Repository(Path("/work"))
