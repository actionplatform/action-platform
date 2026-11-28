"""action_platform.core.flow.remote_audit — the git-flow audit over what a host compares, without a clone."""

from __future__ import annotations

import unittest

from action_platform.core.context import CommitRow, TagRow
from action_platform.core.flow.remote import RemoteRefs
from action_platform.core.flow.remote_audit import audit


def c(sha: str, subject: str) -> CommitRow:
    return CommitRow(sha=sha, subject=subject, author=None, date=None)


class Reader:
    def __init__(self, compares=None, touching=None):
        self.compares = compares or {}
        self.touching = touching or []
        self.asked = []

    def compare(self, repo, base, head):
        self.asked.append(("compare", base, head))

        return self.compares.get((base, head), [])

    def commits(self, repo, ref, limit=50, path=None):
        self.asked.append(("commits", ref, path))

        return self.touching

    def file(self, repo, ref, path):
        return None

    def tags(self, repo):
        return []


REFS = RemoteRefs(branches={"develop": "d", "master": "m", "feature/7-x": "f"})
TAGS = [TagRow(name="v1.1.0", sha="t", date=None, subject=None)]


class RemoteAuditTest(unittest.TestCase):
    def test_a_work_branch_checks_what_develop_does_not_have(self):
        reader = Reader(
            {("develop", "feature/7-x"): [c("2", "update stuff"), c("1", "feat: x")]}
        )
        report = audit(reader, "acme/x", "feature/7-x", REFS, TAGS)

        self.assertEqual(report.checked_commits, 2)
        self.assertEqual(len(report.problems), 1)
        self.assertEqual(reader.asked, [("compare", "develop", "feature/7-x")])

    def test_a_badly_named_branch_without_a_base_is_one_problem(self):
        report = audit(Reader(), "acme/x", "wip", RemoteRefs(branches={"wip": "w"}), [])

        self.assertEqual((report.checked_commits, len(report.problems)), (0, 1))

    def test_a_protected_branch_checks_after_the_tag_and_after_platform_toml(self):
        reader = Reader(
            {
                ("i", "master"): [
                    c("3", "fix: after both"),
                    c("2", "chore: before tag"),
                ],
                ("v1.1.0", "master"): [
                    c("3", "fix: after both"),
                    c("0", "older merge"),
                ],
            },
            touching=[c("5", "chore: edit toml"), c("i", "chore: add platform.toml")],
        )
        report = audit(reader, "acme/x", "master", REFS, TAGS)

        self.assertEqual(report.checked_commits, 1)
        self.assertTrue(report.ok)
        self.assertIn(("commits", "master", "platform.toml"), reader.asked)

    def test_a_protected_branch_never_installed_checks_since_the_tag(self):
        reader = Reader({("v1.1.0", "master"): [c("3", "bad commit")]})
        report = audit(reader, "acme/x", "master", REFS, TAGS)

        self.assertEqual((report.checked_commits, len(report.problems)), (1, 1))

    def test_a_protected_branch_without_tag_or_install_checks_nothing(self):
        report = audit(Reader(), "acme/x", "master", REFS, [])

        self.assertEqual(report.checked_commits, 0)
        self.assertTrue(report.ok)
