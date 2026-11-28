"""action_platform.core.flow.remote — a remote's branches, tags and default branch from `git ls-remote`, without a clone."""

from __future__ import annotations

import subprocess
import unittest

from action_platform.core.flow.remote import parse, remote_refs
from action_platform.core.flow.repo.sync import SyncError

LISTING = (
    "ref: refs/heads/master\tHEAD\n"
    "aaa\tHEAD\n"
    "aaa\trefs/heads/master\n"
    "bbb\trefs/heads/feature/7-x\n"
    "ccc\trefs/tags/v1.0.0\n"
    "ddd\trefs/tags/v1.0.0^{}\n"
    "eee\trefs/tags/v0.9.0\n"
    "fff\trefs/pull/7/head\n"
)


class RemoteRefsTest(unittest.TestCase):
    def test_branches_tags_peeled_and_the_default_branch(self):
        refs = parse(LISTING)

        self.assertEqual(refs.branches, {"master": "aaa", "feature/7-x": "bbb"})
        self.assertEqual(refs.tags, {"v1.0.0": "ddd", "v0.9.0": "eee"})
        self.assertEqual(refs.default_branch, "master")

    def test_the_digest_moves_only_when_a_ref_moves(self):
        same = parse(
            LISTING.replace("bbb\trefs/heads/feature/7-x\n", "")
            + "bbb\trefs/heads/feature/7-x\n"
        )
        moved = parse(LISTING.replace("bbb\t", "bbc\t"))

        self.assertEqual(parse(LISTING).digest, same.digest)
        self.assertNotEqual(parse(LISTING).digest, moved.digest)

    def test_runs_ls_remote_with_symref(self):
        calls = []

        def runner(args, cwd=None):
            calls.append(args)

            return subprocess.CompletedProcess(args, 0, LISTING, "")

        refs = remote_refs("https://github.com/acme/x.git", runner)

        self.assertEqual(
            calls, [["ls-remote", "--symref", "https://github.com/acme/x.git"]]
        )
        self.assertEqual(refs.default_branch, "master")

    def test_a_refused_remote_raises_a_sync_error(self):
        def runner(args, cwd=None):
            return subprocess.CompletedProcess(
                args, 128, "", "fatal: Authentication failed"
            )

        with self.assertRaises(SyncError):
            remote_refs("https://github.com/acme/x.git", runner)
