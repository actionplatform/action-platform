"""action_platform.cli.commands.login — what `login` and `whoami` print."""

from __future__ import annotations

import unittest

from pydantic import ValidationError

from action_platform.cli.commands.login import _describe
from action_platform.remote.credentials import Credentials
from action_platform.remote.schemas import Me


class DescribeTest(unittest.TestCase):
    def test_names_the_reach(self):
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
        self.assertEqual(
            _describe(creds, Me(user={}, project={"id": "p1"})),
            "? — scope: read write — on p1",
        )

    def test_a_reach_that_is_not_an_object_is_refused_at_the_boundary(self):
        with self.assertRaises(ValidationError):
            Me.model_validate({"user": {}, "project": "shop"})
