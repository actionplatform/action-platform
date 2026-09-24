"""action_platform.cli.commands.login — what `login` and `whoami` print."""

from __future__ import annotations

import unittest

from action_platform.cli.commands.login import _describe
from action_platform.remote.credentials import Credentials
from action_platform.remote.schemas import Me


class DescribeTest(unittest.TestCase):
    def test_names_the_reach_from_objects_or_strings(self):
        creds = Credentials("https://p.example", "t", "read write")
        who = Me(
            user={"email": "me@example.com"},
            organization={"id": "o1", "name": "Acme"},
            scope=["read", "write"],
            project={"id": "p1", "name": "Shop"},
            app={"id": "a1", "name": "orders", "registry_id": "r1"},
        )

        self.assertEqual(
            _describe(creds, who),
            "me@example.com — scope: read write — on Acme / Shop / orders",
        )
        self.assertEqual(
            _describe(creds, Me(user={"email": "me@example.com"})),
            "me@example.com — scope: read write",
        )
