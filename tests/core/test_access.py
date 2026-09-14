"""Roles, permissions, scopes and grants: the rules every surface applies."""

import unittest

from action_platform.core.access import (
    Grant,
    can,
    grantable_scopes,
    grants_of,
    normalize_role,
    parse_scopes,
    scope_allows,
)


class AccessTest(unittest.TestCase):
    def test_roles_and_permissions(self):
        self.assertTrue(can("owner", "org.manage"))
        self.assertTrue(can("deployer", "app.release"))
        self.assertFalse(can("developer", "app.release"))
        self.assertFalse(can("viewer", "app.sync"))
        self.assertFalse(can(None, "app.sync"))
        self.assertEqual(normalize_role("member"), "developer")
        self.assertIsNone(normalize_role("king"))
        self.assertEqual(sum(grants_of("developer").values()), 3)

    def test_scopes(self):
        self.assertEqual(
            parse_scopes("write, admin read bogus"), ["read", "write", "admin"]
        )
        self.assertTrue(scope_allows(["read", "write"], "app.flow"))
        self.assertFalse(scope_allows(["read"], "app.flow"))
        self.assertFalse(scope_allows(["write"], None))
        self.assertTrue(scope_allows(["read"], None))
        self.assertEqual(grantable_scopes("developer"), ["read", "write"])
        self.assertEqual(grantable_scopes("deployer"), ["read", "write", "release"])
        self.assertEqual(
            grantable_scopes("owner"), ["read", "write", "release", "admin"]
        )
        self.assertEqual(grantable_scopes(None), ["read"])

    def test_grant_round_trip(self):
        grant = Grant(["read", "write"], "o1", "p1", "a1")
        self.assertEqual(grant.format(), "read write org:o1 project:p1 app:a1")
        self.assertEqual(Grant.parse(grant.format()), grant)
        self.assertEqual(Grant.parse("read"), Grant(["read"]))
        self.assertEqual(Grant.parse(None), Grant())
