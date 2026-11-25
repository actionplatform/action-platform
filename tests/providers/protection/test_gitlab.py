"""action_platform.providers.protection.gitlab — protected branches, "pipelines must succeed" and push rules, Free and Premium."""

from __future__ import annotations

import unittest

from action_platform.core.flow.protection import (
    BRANCH_PATTERN,
    COMMIT_PATTERN,
    CHECK,
    INACTIVE,
    NATIVE,
    Policy,
)
from action_platform.providers.protection.gitlab import FREE_PUSH, GitlabProtection
from action_platform.testing.hosts import FakeHost, refused

PROJECT = "/projects/acme%2Forders"


def policy(checks=("gitflow", "conventional-commit")) -> Policy:
    return Policy(branches=("main", "develop"), checks=checks, identity=None)


class GitlabSimulator:
    def __init__(self, premium: bool) -> None:
        self.branches: dict[str, dict] = {}
        self.project = {"only_allow_merge_if_pipeline_succeeds": False}
        self.rule = None
        routes = {
            ("GET", "/user"): {"id": 9, "username": "ap-bot"},
            ("GET", PROJECT): lambda _: self.project,
            ("PUT", PROJECT): lambda b: self.project.update(b),
            ("POST", f"{PROJECT}/protected_branches"): self.protect,
        }

        if premium:
            routes[("GET", f"{PROJECT}/push_rule")] = lambda _: self.rule
            routes[("POST", f"{PROJECT}/push_rule")] = self.set_rule
            routes[("PUT", f"{PROJECT}/push_rule")] = self.set_rule
        else:
            routes[("GET", f"{PROJECT}/push_rule")] = refused(404, "404 Not Found")

        self.host = FakeHost(routes)
        self.premium = premium

    def set_rule(self, body):
        self.rule = dict(body)

        return self.rule

    def patch(self, name, body):
        row = self.branches[name]

        if "allow_force_push" in body:
            row["allow_force_push"] = body["allow_force_push"]

        for item in body.get("allowed_to_push") or []:
            if item.get("_destroy"):
                row["push_access_levels"] = [
                    level
                    for level in row["push_access_levels"]
                    if level["id"] != item["id"]
                ]
            else:
                row["push_access_levels"].append(
                    {"id": 99, "access_level": 40, "user_id": item.get("user_id")}
                )

        return row

    def protect(self, body):
        name = body["name"]
        levels = []

        if body.get("push_access_level") is not None:
            levels.append(
                {"id": 1, "access_level": body["push_access_level"], "user_id": None}
            )

        for item in body.get("allowed_to_push") or []:
            levels.append({"id": 2, "access_level": 40, "user_id": item.get("user_id")})

        row = {
            "name": name,
            "allow_force_push": body.get("allow_force_push", False),
            "push_access_levels": levels,
        }
        self.branches[name] = row
        path = f"{PROJECT}/protected_branches/{name}"
        self.host.routes[("GET", path)] = lambda _: self.branches[name]
        self.host.routes[("PATCH", path)] = lambda b: self.patch(name, b)

        return row


class PremiumTest(unittest.TestCase):
    def test_only_the_platform_account_pushes(self):
        sim = GitlabSimulator(premium=True)
        state = GitlabProtection("acme/orders", "t", send=sim.host).apply(policy())

        posts = [
            b for p, b in sim.host.sent("POST") if p.endswith("/protected_branches")
        ]
        self.assertEqual(
            posts[0],
            {
                "name": "main",
                "merge_access_level": 30,
                "allow_force_push": False,
                "push_access_level": 0,
                "allowed_to_push": [{"user_id": 9}],
            },
        )
        self.assertEqual(
            sim.project,
            {
                "only_allow_merge_if_pipeline_succeeds": True,
                "allow_merge_on_skipped_pipeline": False,
            },
        )
        self.assertEqual(
            sim.rule,
            {
                "commit_message_regex": COMMIT_PATTERN,
                "branch_name_regex": BRANCH_PATTERN,
            },
        )
        self.assertEqual(state.drift, [])
        modes = {r.rule: r.mode for r in state.rules}
        self.assertEqual(modes["direct_push"], NATIVE)
        self.assertEqual(modes["required_checks"], NATIVE)
        self.assertEqual(modes["branch_names"], NATIVE)
        self.assertEqual(state.bypass, "ap-bot")

    def test_a_maintainer_added_to_push_access_is_drift_and_reapplied(self):
        sim = GitlabSimulator(premium=True)
        provider = GitlabProtection("acme/orders", "t", send=sim.host)
        provider.apply(policy())
        sim.branches["main"]["push_access_levels"].append(
            {"id": 3, "access_level": 40, "user_id": None}
        )

        drifted = provider.status(policy())
        self.assertIn("main: push access differs from the policy", drifted.drift)
        self.assertEqual(drifted.rule("direct_push").mode, INACTIVE)

        fixed = provider.apply(policy())
        self.assertEqual(fixed.drift, [])
        self.assertIn(
            (
                f"{PROJECT}/protected_branches/main",
                {"allowed_to_push": [{"id": 3, "_destroy": True}]},
            ),
            sim.host.sent("PATCH"),
        )
        self.assertEqual(sim.host.sent("DELETE"), [])


class FreeTest(unittest.TestCase):
    def test_free_never_widens_an_existing_branch(self):
        sim = GitlabSimulator(premium=False)
        sim.protect({"name": "main", "push_access_level": 0, "allow_force_push": True})
        state = GitlabProtection("acme/orders", "t", send=sim.host).apply(policy())

        self.assertEqual(
            sim.host.sent("PATCH"),
            [(f"{PROJECT}/protected_branches/main", {"allow_force_push": False})],
        )
        self.assertEqual(
            sim.branches["main"]["push_access_levels"][0]["access_level"], 0
        )
        self.assertEqual(state.bypass, "Maintainers (GitLab Free)")

    def test_no_ci_checks_leave_pipelines_alone(self):
        sim = GitlabSimulator(premium=False)
        state = GitlabProtection("acme/orders", "t", send=sim.host).apply(
            policy(checks=())
        )

        self.assertEqual(sim.host.sent("PUT"), [])
        self.assertNotIn("pipelines must succeed is off", state.drift)

    def test_free_keeps_maintainers_and_says_so(self):
        sim = GitlabSimulator(premium=False)
        state = GitlabProtection("acme/orders", "t", send=sim.host).apply(policy())

        post = next(
            b for p, b in sim.host.sent("POST") if p.endswith("/protected_branches")
        )
        self.assertEqual(post["push_access_level"], 40)
        self.assertNotIn("allowed_to_push", post)
        self.assertEqual(state.rule("direct_push").mode, INACTIVE)
        self.assertEqual(state.rule("direct_push").detail, FREE_PUSH)
        self.assertEqual(state.rule("force_push").mode, NATIVE)
        self.assertEqual(state.rule("required_checks").mode, NATIVE)
        self.assertEqual(state.rule("branch_names").mode, CHECK)
        self.assertEqual(state.bypass, "Maintainers (GitLab Free)")
        self.assertTrue(state.active)

    def test_no_ci_checks_leaves_names_inactive(self):
        sim = GitlabSimulator(premium=False)
        state = GitlabProtection("acme/orders", "t", send=sim.host).apply(
            policy(checks=())
        )

        self.assertEqual(state.rule("required_checks").mode, INACTIVE)
        self.assertEqual(state.rule("commit_messages").mode, INACTIVE)

    def test_a_refusal_is_the_reason(self):
        sim = GitlabSimulator(premium=False)
        sim.host.routes[("POST", f"{PROJECT}/protected_branches")] = refused(
            403, "403 Forbidden"
        )
        state = GitlabProtection("acme/orders", "t", send=sim.host).apply(policy())

        self.assertFalse(state.active)
        self.assertIn("Maintainer", state.error)


if __name__ == "__main__":
    unittest.main()
