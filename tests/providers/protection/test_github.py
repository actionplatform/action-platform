"""action_platform.providers.protection.github — rulesets as the REST API documents them, applied, read back and compared."""

from __future__ import annotations

import unittest

from action_platform.core.flow.protection import (
    CHECK,
    INACTIVE,
    NATIVE,
    Identity,
    Policy,
)
from action_platform.providers.protection.github import (
    NAMES_RULESET,
    RULESET,
    GithubProtection,
)
from action_platform.testing.hosts import FakeHost, refused

APP = Identity("github_app", "4242", "action-platform")
REPO = "acme/orders"
BASE = f"/repos/{REPO}"


def policy(**kw) -> Policy:
    return Policy(
        branches=kw.get("branches", ("main", "develop")),
        checks=kw.get("checks", ("gitflow", "conventional-commit", "jenkins/ci")),
        identity=kw.get("identity", APP),
    )


class GithubSimulator:
    """Rulesets kept in memory the way the repository rulesets endpoints keep them."""

    def __init__(self, plan: str = "team") -> None:
        self.rulesets: dict[int, dict] = {}
        self.host = FakeHost(
            {
                ("GET", f"{BASE}/rulesets?includes_parents=false"): lambda _: [
                    {"id": i, "name": r["name"], "source_type": "Repository"}
                    for i, r in self.rulesets.items()
                ],
                ("POST", f"{BASE}/rulesets"): self.create,
                ("GET", BASE): {"owner": {"login": "acme", "type": "Organization"}},
                ("GET", "/orgs/acme"): {"plan": {"name": plan}},
            }
        )

    def create(self, body: dict) -> dict:
        id = len(self.rulesets) + 1
        self.rulesets[id] = {"id": id, "source_type": "Repository", **body}
        self.host.routes[("GET", f"{BASE}/rulesets/{id}")] = lambda _: self.rulesets[id]
        self.host.routes[("PUT", f"{BASE}/rulesets/{id}")] = lambda b: self.rulesets[
            id
        ].update(b)
        self.host.routes[("GET", f"{BASE}/rulesets/{id}/history?per_page=1")] = [
            {"version_id": 2, "actor": {"id": 77, "type": "User"}}
        ]

        return self.rulesets[id]


class ApplyTest(unittest.TestCase):
    def test_creates_one_ruleset_with_the_documented_rules(self):
        sim = GithubSimulator()
        state = GithubProtection(REPO, "t", app=APP, send=sim.host).apply(policy())

        ((path, body),) = sim.host.sent("POST")
        self.assertEqual(path, f"{BASE}/rulesets")
        self.assertEqual(body["name"], RULESET)
        self.assertEqual(body["enforcement"], "active")
        self.assertEqual(
            body["bypass_actors"],
            [{"actor_id": 4242, "actor_type": "Integration", "bypass_mode": "always"}],
        )
        self.assertEqual(
            body["conditions"]["ref_name"]["include"],
            ["refs/heads/main", "refs/heads/develop"],
        )
        types = [r["type"] for r in body["rules"]]
        self.assertEqual(
            types,
            ["deletion", "non_fast_forward", "pull_request", "required_status_checks"],
        )
        pull = body["rules"][2]["parameters"]
        self.assertEqual(pull["required_approving_review_count"], 0)
        self.assertEqual(
            set(pull),
            {
                "required_approving_review_count",
                "dismiss_stale_reviews_on_push",
                "require_code_owner_review",
                "require_last_push_approval",
                "required_review_thread_resolution",
            },
        )
        self.assertEqual(
            body["rules"][3]["parameters"]["required_status_checks"],
            [
                {"context": "gitflow"},
                {"context": "conventional-commit"},
                {"context": "jenkins/ci"},
            ],
        )
        self.assertTrue(state.active)
        self.assertEqual(state.drift, [])
        modes = {r.rule: r.mode for r in state.rules}
        self.assertEqual(modes["direct_push"], NATIVE)
        self.assertEqual(modes["required_checks"], NATIVE)
        self.assertEqual(modes["branch_names"], CHECK)
        self.assertEqual(modes["commit_messages"], CHECK)
        self.assertEqual(state.bypass, "GitHub App action-platform")

    def test_enterprise_adds_the_names_ruleset(self):
        sim = GithubSimulator(plan="enterprise")
        state = GithubProtection(REPO, "t", app=APP, send=sim.host).apply(policy())

        names = [b["name"] for _, b in sim.host.sent("POST")]
        self.assertEqual(names, [RULESET, NAMES_RULESET])
        rules = {r["type"]: r["parameters"] for r in sim.rulesets[2]["rules"]}
        self.assertEqual(rules["branch_name_pattern"]["operator"], "regex")
        self.assertEqual(sim.rulesets[2]["conditions"]["ref_name"]["include"], ["~ALL"])
        self.assertEqual(state.rule("branch_names").mode, NATIVE)
        self.assertEqual(state.rule("commit_messages").mode, NATIVE)

    def test_no_checks_skips_the_status_rule(self):
        sim = GithubSimulator()
        state = GithubProtection(REPO, "t", app=APP, send=sim.host).apply(
            policy(checks=())
        )

        self.assertNotIn(
            "required_status_checks", [r["type"] for r in sim.rulesets[1]["rules"]]
        )
        self.assertEqual(state.rule("required_checks").mode, INACTIVE)
        self.assertEqual(state.rule("branch_names").mode, INACTIVE)

    def test_existing_ruleset_is_replaced_not_duplicated(self):
        sim = GithubSimulator()
        provider = GithubProtection(REPO, "t", app=APP, send=sim.host)
        provider.apply(policy())
        provider.apply(policy())

        self.assertEqual(len(sim.host.sent("POST")), 1)
        self.assertEqual(len(sim.host.sent("PUT")), 1)

    def test_without_the_platform_identity_nothing_is_sent(self):
        sim = GithubSimulator()
        state = GithubProtection(REPO, "t", send=sim.host).apply(policy(identity=None))

        self.assertEqual(sim.host.calls, [])
        self.assertFalse(state.active)
        self.assertIn("GitHub App", state.error)

    def test_plan_refusal_is_the_reason_shown(self):
        sim = GithubSimulator()
        sim.host.routes[("GET", f"{BASE}/rulesets?includes_parents=false")] = refused(
            403,
            "Upgrade to GitHub Pro or make this repository public to enable this feature.",
        )
        state = GithubProtection(REPO, "t", app=APP, send=sim.host).apply(policy())

        self.assertFalse(state.active)
        self.assertIn("Upgrade to GitHub Pro", state.error)
        self.assertTrue(all(r.mode == INACTIVE for r in state.rules))


class DriftTest(unittest.TestCase):
    def setUp(self):
        self.sim = GithubSimulator()
        self.provider = GithubProtection(REPO, "t", app=APP, send=self.sim.host)
        self.provider.apply(policy())

    def test_a_human_bypass_and_a_removed_rule_are_drift(self):
        ruleset = self.sim.rulesets[1]
        ruleset["bypass_actors"].append(
            {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
        )
        ruleset["rules"] = [
            r for r in ruleset["rules"] if r["type"] != "non_fast_forward"
        ]

        state = self.provider.status(policy())

        self.assertIn("bypass granted to RepositoryRole 5", state.drift)
        self.assertIn("rule `non_fast_forward` missing", state.drift)
        self.assertEqual(state.rule("force_push").mode, INACTIVE)
        self.assertEqual(state.changed_by, "User 77")

    def test_disabled_enforcement_turns_every_native_rule_off(self):
        self.sim.rulesets[1]["enforcement"] = "disabled"

        state = self.provider.status(policy())

        self.assertFalse(state.active)
        self.assertIn("ruleset enforcement is disabled", state.drift)

    def test_deleted_ruleset_is_drift_without_an_error(self):
        self.sim.rulesets.clear()

        state = self.provider.status(policy())

        self.assertIsNone(state.error)
        self.assertFalse(state.active)
        self.assertEqual(state.drift, [f"ruleset `{RULESET}` missing"])


class ContextsTest(unittest.TestCase):
    def test_statuses_from_the_ci_origin_on_merged_pull_requests(self):
        host = FakeHost(
            {
                ("GET", f"{BASE}/pulls?state=closed&per_page=20"): [
                    {"merged_at": "2026-11-20T10:00:00Z", "head": {"sha": "a1"}},
                    {"merged_at": None, "head": {"sha": "b2"}},
                ],
                ("GET", f"{BASE}/commits/a1/status"): {
                    "statuses": [
                        {
                            "context": "jenkins/ci",
                            "target_url": "https://jenkins.acme.io/job/x/1/",
                        },
                        {"context": "other", "target_url": "https://ci.example.org/1"},
                    ]
                },
            }
        )

        found = GithubProtection(REPO, "t", app=APP, send=host).contexts(
            "https://jenkins.acme.io"
        )

        self.assertEqual(found, ("jenkins/ci",))


if __name__ == "__main__":
    unittest.main()
