"""app.services.workspace.checkout.clone_problem — a failed clone says what to fix."""

from __future__ import annotations

import unittest

from app.services.workspace.checkout import clone_problem

URL = "https://github.com/acme/private.git"


class CloneProblemTest(unittest.TestCase):
    def test_a_refused_org_repository_names_where_access_is_granted(self):
        message = clone_problem(
            URL,
            "remote: Write access to repository not granted.\n"
            "fatal: unable to access 'https://github.com/acme/private.git/': The requested URL returned error: 403\n",
        )

        self.assertTrue(
            message.startswith("cannot read acme/private: the code host refused")
        )
        self.assertIn("Third-party access", message)
        self.assertIn("GitHub App", message)
        self.assertNotIn("Write access", message)

    def test_another_host_is_told_to_reconnect(self):
        message = clone_problem(
            "https://gitlab.com/acme/private.git",
            "fatal: Authentication failed for 'https://gitlab.com/acme/private.git/'",
        )

        self.assertIn("Reconnect the host in Settings", message)
        self.assertNotIn("GitHub", message)

    def test_a_missing_repository_may_be_hidden(self):
        message = clone_problem(
            URL, "remote: Repository not found.\nfatal: repository not found"
        )

        self.assertEqual(
            message,
            "cannot read acme/private: it does not exist, or the connected account cannot see it",
        )

    def test_anything_else_keeps_git_s_last_line(self):
        self.assertEqual(
            clone_problem(URL, "warning: x\nfatal: early EOF\n"),
            "clone failed: fatal: early EOF",
        )
