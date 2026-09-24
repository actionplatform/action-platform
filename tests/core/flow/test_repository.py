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
