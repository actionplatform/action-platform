"""action_platform.providers.protection.bitbucket — branch restrictions as the 2.0 API documents them."""

from __future__ import annotations

import unittest

from action_platform.core.flow.protection import CHECK, INACTIVE, NATIVE, Policy
from action_platform.providers.protection.bitbucket import BitbucketProtection
from action_platform.testing.hosts import FakeHost, refused

LIST = "/repositories/acme/orders/branch-restrictions?pagelen=100"
CREATE = "/repositories/acme/orders/branch-restrictions"
ME = "{1111-2222}"


def policy(checks=("gitflow", "conventional-commit")) -> Policy:
    return Policy(branches=("main",), checks=checks, identity=None)


class BitbucketSimulator:
    def __init__(self) -> None:
        self.rows: dict[int, dict] = {}
        self.host = FakeHost(
            {
                ("GET", "/user"): {"uuid": ME, "display_name": "AP Bot"},
                ("GET", LIST): lambda _: {"values": list(self.rows.values())},
                ("POST", CREATE): self.create,
            }
        )

    def create(self, body):
        id = len(self.rows) + 1
        self.rows[id] = {"id": id, "users": [], "groups": [], **body}
        self.host.routes[("PUT", f"{CREATE}/{id}")] = lambda b: self.rows[id].update(b)

        return self.rows[id]


class ApplyTest(unittest.TestCase):
    def test_restrictions_per_branch_with_the_platform_as_the_only_pusher(self):
        sim = BitbucketSimulator()
        state = BitbucketProtection("acme/orders", "t", send=sim.host).apply(policy())

        bodies = {b["kind"]: b for _, b in sim.host.sent("POST")}
        self.assertEqual(
            set(bodies),
            {
                "push",
                "force",
                "delete",
                "require_passing_builds_to_merge",
                "enforce_merge_checks",
            },
        )
        self.assertEqual(
            bodies["push"],
            {
                "branch_match_kind": "glob",
                "pattern": "main",
                "kind": "push",
                "users": [{"uuid": ME}],
                "groups": [],
            },
        )
        self.assertEqual(bodies["require_passing_builds_to_merge"]["value"], 2)
        self.assertEqual(state.drift, [])
        self.assertEqual(state.rule("direct_push").mode, NATIVE)
        self.assertEqual(state.rule("required_checks").mode, CHECK)
        self.assertIn("Premium", state.rule("required_checks").detail)
        self.assertEqual(state.bypass, "AP Bot")

    def test_an_added_user_is_drift_and_put_back(self):
        sim = BitbucketSimulator()
        provider = BitbucketProtection("acme/orders", "t", send=sim.host)
        provider.apply(policy())
        push = next(r for r in sim.rows.values() if r["kind"] == "push")
        push["users"].append({"uuid": "{human}"})

        drifted = provider.status(policy())
        self.assertIn("main: `push` restriction differs from the policy", drifted.drift)
        self.assertEqual(drifted.rule("direct_push").mode, INACTIVE)

        fixed = provider.apply(policy())
        self.assertEqual(fixed.drift, [])
        self.assertEqual(len(sim.host.sent("PUT")), 1)

    def test_no_account_behind_the_token_refuses(self):
        sim = BitbucketSimulator()
        sim.host.routes[("GET", "/user")] = refused(403, "access token")
        state = BitbucketProtection("acme/orders", "t", send=sim.host).apply(policy())

        self.assertFalse(state.active)
        self.assertIn("GET /user", state.error)
        self.assertEqual(sim.host.sent("POST"), [])


if __name__ == "__main__":
    unittest.main()
