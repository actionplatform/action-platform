import unittest

from action_platform.core.service_access import AccessError

from action_platform.providers.access.github.checks import Org
from action_platform.testing.github import FakeGitHub

CLASSIC = {
    "url": "https://api.github.com/repos/acme/api/branches/main/protection",
    "required_status_checks": {
        "strict": True,
        "contexts": ["build"],
        "checks": [{"context": "build", "app_id": 15368}],
    },
    "enforce_admins": {"enabled": True},
    "required_pull_request_reviews": {
        "dismiss_stale_reviews": True,
        "require_code_owner_reviews": False,
        "required_approving_review_count": 2,
    },
    "required_linear_history": {"enabled": False},
    "allow_force_pushes": {"enabled": False},
    "allow_deletions": {"enabled": False},
}


class Protection(unittest.TestCase):
    def setUp(self):
        self.github = FakeGitHub()
        self.org = Org(self.github, "acme")

    def one(self, name="api"):
        return next(r for r in self.org.branch_protection().repos if r.repo == name)

    def test_an_unprotected_branch_says_so(self):
        self.github.repo("api")

        r = self.one()

        self.assertIs(r.protected, False)
        self.assertEqual(r.required_reviews, 0)
        self.assertEqual(r.required_status_checks, [])
        self.assertIs(r.force_pushes_allowed, True)
        self.assertEqual(r.note, "")

    def test_a_protection_rule_is_read(self):
        self.github.repo("api")
        self.github.protection["api"] = CLASSIC

        r = self.one()

        self.assertIs(r.protected, True)
        self.assertEqual(r.required_reviews, 2)
        self.assertEqual(r.required_status_checks, ["build"])
        self.assertIs(r.force_pushes_allowed, False)

    def test_force_pushes_enabled_on_a_protection_rule(self):
        self.github.repo("api")
        self.github.protection["api"] = {
            **CLASSIC,
            "allow_force_pushes": {"enabled": True},
        }

        self.assertIs(self.one().force_pushes_allowed, True)

    def test_a_ruleset_protects_without_a_rule(self):
        self.github.repo("api")
        self.github.rules["api"] = [
            {
                "type": "pull_request",
                "parameters": {"required_approving_review_count": 1},
                "ruleset_source_type": "Repository",
                "ruleset_source": "acme/api",
                "ruleset_id": 4898070,
            },
            {
                "type": "required_status_checks",
                "parameters": {
                    "required_status_checks": [{"context": "lint", "integration_id": 1}]
                },
            },
            {"type": "non_fast_forward"},
        ]

        r = self.one()

        self.assertIs(r.protected, True)
        self.assertEqual(
            r.rule_types, ["non_fast_forward", "pull_request", "required_status_checks"]
        )
        self.assertEqual(r.required_reviews, 1)
        self.assertEqual(r.required_status_checks, ["lint"])
        self.assertIs(r.force_pushes_allowed, False)

    def test_rule_and_ruleset_add_up(self):
        self.github.repo("api")
        self.github.protection["api"] = CLASSIC
        self.github.rules["api"] = [
            {
                "type": "pull_request",
                "parameters": {"required_approving_review_count": 3},
            },
            {
                "type": "required_status_checks",
                "parameters": {"required_status_checks": [{"context": "lint"}]},
            },
        ]

        r = self.one()

        self.assertEqual(r.required_reviews, 3)
        self.assertEqual(r.required_status_checks, ["build", "lint"])

    def test_a_repository_the_plan_hides_is_noted_not_guessed(self):
        self.github.repo("api")
        self.github.repo("private", private=True, visibility="private")
        self.github.denied.add("private")

        r = self.one("private")

        self.assertIsNone(r.protected)
        self.assertIsNone(r.required_reviews)
        self.assertIsNone(r.force_pushes_allowed)
        self.assertIn("403", r.note)
        self.assertEqual(self.one("api").note, "")

    def test_one_repository(self):
        self.github.repo("api")
        self.github.repo("site")

        out = self.org.branch_protection("site")

        self.assertEqual([r.repo for r in out.repos], ["site"])

    def test_an_unknown_repository_is_an_error(self):
        with self.assertRaisesRegex(AccessError, "answered 404"):
            self.org.branch_protection("nope")

    def test_reads_only(self):
        self.github.repo("api")
        self.org.branch_protection()
        self.org.repo_settings()

        self.assertEqual(self.github.writes(), [])

    def test_every_page_is_read(self):
        self.github.page = 2

        for n in range(5):
            self.github.repo(f"r{n}")

        self.assertEqual(len(self.org.branch_protection().repos), 5)


class Settings(unittest.TestCase):
    def setUp(self):
        self.github = FakeGitHub()
        self.org = Org(self.github, "acme")

    def test_settings_come_from_the_full_record(self):
        self.github.repo(
            "api",
            delete_branch_on_merge=True,
            allow_auto_merge=True,
            security_and_analysis={
                "dependabot_security_updates": {"status": "enabled"},
                "secret_scanning": {"status": "enabled"},
                "secret_scanning_push_protection": {"status": "disabled"},
            },
        )
        self.github.alerts["api"] = True

        r = self.org.repo_settings().repos[0]

        self.assertEqual(
            (r.repo, r.visibility, r.default_branch, r.archived),
            ("api", "public", "main", False),
        )
        self.assertIs(r.delete_branch_on_merge, True)
        self.assertIs(r.allow_auto_merge, True)
        self.assertEqual(r.secret_scanning, "enabled")
        self.assertEqual(r.secret_scanning_push_protection, "disabled")
        self.assertEqual(r.dependabot_security_updates, "enabled")
        self.assertIs(r.dependabot_alerts, True)

    def test_disabled_alerts_are_false(self):
        self.github.repo("api")

        self.assertIs(self.org.repo_settings().repos[0].dependabot_alerts, False)

    def test_what_the_token_cannot_see_is_null(self):
        doc = self.github.repo("api", visibility="private", private=True)
        del doc["security_and_analysis"]

        r = self.org.repo_settings().repos[0]

        self.assertEqual(r.visibility, "private")
        self.assertIsNone(r.secret_scanning)
        self.assertIsNone(r.dependabot_security_updates)

    def test_one_repository(self):
        self.github.repo("api")
        self.github.repo("site")

        self.assertEqual(
            [r.repo for r in self.org.repo_settings("site").repos], ["site"]
        )
