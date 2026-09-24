"""action_platform.core.flow.repository — git commands through an injected runner, no subprocess or disk."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

from action_platform.core.flow.repository import Repository, subprocess_git


class FakeGit:
    def __init__(
        self, answers: dict[tuple[str, ...], tuple[int, str, str]] | None = None
    ):
        self.answers = answers or {}
        self.calls: list[tuple[list[str], Path | None]] = []

    def __call__(self, args, cwd=None):
        self.calls.append((list(args), cwd))
        code, out, err = self.answers.get(tuple(args), (0, "", ""))

        return subprocess.CompletedProcess(["git", *args], code, out, err)


class RunnerSeamTest(unittest.TestCase):
    def test_defaults_to_subprocess(self):
        self.assertIs(Repository(Path("/nowhere")).runner, subprocess_git)

    def test_run_goes_through_the_runner_in_the_clone(self):
        fake = FakeGit({("rev-parse", "HEAD"): (0, "abc123\n", "")})
        repo = Repository(Path("/work"), runner=fake)

        self.assertEqual(repo.head, "abc123")
        self.assertEqual(fake.calls, [(["rev-parse", "HEAD"], Path("/work"))])

    def test_run_raises_on_failure_and_attempt_does_not(self):
        fake = FakeGit({("push", "origin", "HEAD"): (1, "", "rejected")})
        repo = Repository(Path("/work"), runner=fake)

        with self.assertRaises(subprocess.CalledProcessError) as caught:
            repo.push()

        self.assertEqual(caught.exception.stderr, "rejected")
        self.assertEqual(repo.attempt(["push", "origin", "HEAD"]).returncode, 1)

    def test_clone_and_init_use_the_runner(self):
        fake = FakeGit()
        cloned = Repository.clone(
            "https://example.com/a.git", Path("/work/a"), depth=1, runner=fake
        )
        Repository.init(Path("/work/b"), runner=fake)

        self.assertIs(cloned.runner, fake)
        self.assertEqual(
            fake.calls[0],
            (
                [
                    "clone",
                    "--quiet",
                    "--depth",
                    "1",
                    "--end-of-options",
                    "https://example.com/a.git",
                    "/work/a",
                ],
                None,
            ),
        )
        self.assertEqual(fake.calls[1], (["init", "-q", "-b", "main"], Path("/work/b")))

    def test_clone_failure_raises(self):
        args = ("clone", "--quiet", "--end-of-options", "https://x/a.git", "/w")
        fake = FakeGit({args: (128, "", "not found")})

        with self.assertRaises(subprocess.CalledProcessError):
            Repository.clone("https://x/a.git", Path("/w"), runner=fake)


class AbsentOrFailedTest(unittest.TestCase):
    def repo(self, answers):
        return Repository(Path("/work"), runner=FakeGit(answers))

    def test_missing_remote_is_empty_but_a_broken_clone_raises(self):
        get_url = ("remote", "get-url", "origin")

        self.assertEqual(
            self.repo({get_url: (2, "", "error: No such remote")}).remote_url(), ""
        )

        with self.assertRaises(subprocess.CalledProcessError):
            self.repo({get_url: (128, "", "fatal: not a git repository")}).remote_url()

    def test_no_tag_is_none_but_a_git_failure_raises(self):
        describe = ("describe", "--tags", "--abbrev=0")
        exact = ("describe", "--tags", "--exact-match")
        none = (128, "", "fatal: No names found, cannot describe anything.")
        broken = (128, "", "fatal: not a git repository")

        self.assertIsNone(self.repo({describe: none}).latest_tag())
        self.assertIsNone(
            self.repo(
                {exact: (128, "", "fatal: no tag exactly matches 'abc'")}
            ).tag_at_head()
        )

        with self.assertRaises(subprocess.CalledProcessError):
            self.repo({describe: broken}).latest_tag()

        with self.assertRaises(subprocess.CalledProcessError):
            self.repo({exact: broken}).tag_at_head()

    def test_remote_tag_without_a_remote_is_false_but_an_unreachable_one_raises(self):
        get_url = ("remote", "get-url", "origin")
        ls = ("ls-remote", "--tags", "origin", "refs/tags/v1")
        reachable = (0, "https://x/a.git", "")

        self.assertFalse(
            self.repo({get_url: (2, "", "No such remote")}).remote_tag_exists("v1")
        )
        self.assertTrue(
            self.repo(
                {get_url: reachable, ls: (0, "abc\trefs/tags/v1", "")}
            ).remote_tag_exists("v1")
        )

        with self.assertRaises(subprocess.CalledProcessError):
            self.repo(
                {get_url: reachable, ls: (128, "", "fatal: unable to access")}
            ).remote_tag_exists("v1")

    def test_merge_base_absent_for_unrelated_or_unknown_refs(self):
        args = ("merge-base", "a", "b")

        self.assertIsNone(self.repo({args: (1, "", "")}).merge_base("a", "b"))
        self.assertIsNone(
            self.repo({args: (128, "", "fatal: Not a valid object name b")}).merge_base(
                "a", "b"
            )
        )

        with self.assertRaises(subprocess.CalledProcessError):
            self.repo({args: (128, "", "fatal: not a git repository")}).merge_base(
                "a", "b"
            )

    def test_first_commit_adding_on_an_empty_repository_is_none(self):
        log = ("log", "--diff-filter=A", "--format=%H", "--", "platform.toml")
        empty = "fatal: your current branch 'main' does not have any commits yet"

        self.assertIsNone(
            self.repo({log: (128, "", empty)}).first_commit_adding("platform.toml")
        )
        self.assertEqual(
            self.repo({log: (0, "new\nold\n", "")}).first_commit_adding(
                "platform.toml"
            ),
            "old",
        )

        with self.assertRaises(subprocess.CalledProcessError):
            self.repo({log: (128, "", "fatal: bad object")}).first_commit_adding(
                "platform.toml"
            )

    def test_upstream_absent_only_when_none_is_configured(self):
        args = ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
        none = "fatal: no upstream configured for branch 'x'"

        self.assertIsNone(self.repo({args: (128, "", none)}).upstream())
        self.assertEqual(
            self.repo({args: (0, "origin/x\n", "")}).upstream(), "origin/x"
        )

        with self.assertRaises(subprocess.CalledProcessError):
            self.repo({args: (128, "", "fatal: not a git repository")}).upstream()

    def test_detached_head_falls_back_and_other_failures_raise(self):
        symbolic = ("symbolic-ref", "--short", "-q", "HEAD")
        rev = ("rev-parse", "--abbrev-ref", "HEAD")

        self.assertEqual(
            self.repo({symbolic: (1, "", ""), rev: (0, "HEAD\n", "")}).branch, "HEAD"
        )

        with self.assertRaises(subprocess.CalledProcessError):
            self.repo({symbolic: (128, "", "fatal"), rev: (128, "", "fatal")}).branch

    def test_status_failure_raises_instead_of_reporting_nothing_changed(self):
        args = ("status", "--porcelain=v1", "--untracked-files=all", "-z")

        self.assertEqual(
            self.repo({args: (0, " M a.py\0?? b.py\0", "")}).changed_files(),
            ["a.py", "b.py"],
        )

        with self.assertRaises(subprocess.CalledProcessError):
            self.repo({args: (128, "", "fatal")}).changed_files()
