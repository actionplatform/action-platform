"""The GitHub App: what the manifest asks for, and what the access check says an installation lacks."""

import unittest

from app.services.integrations.hosts.access import AccessReport, Owner
from app.services.integrations.hosts.github import MANIFEST_PERMISSIONS, GithubProvider


class GithubAccessTest(unittest.TestCase):
    def test_manifest_asks_to_write_actions(self):
        self.assertEqual(MANIFEST_PERMISSIONS["actions"], "write")

    def test_installation_without_actions_is_reported(self):
        report = AccessReport(kind="github", login="ada")
        report.installations.append(
            Owner(
                account="acme",
                kind="org",
                repositories="all",
                administration="write",
                contents="write",
                actions="none",
            )
        )

        GithubProvider._check(report, "ada")

        self.assertEqual(len(report.problems), 1)
        self.assertIn('"Actions"', report.problems[0])
        self.assertIn("acme", report.problems[0])

    def test_installation_with_every_permission_is_clean(self):
        report = AccessReport(kind="github", login="ada")
        report.installations.append(
            Owner(
                account="acme",
                kind="org",
                repositories="all",
                administration="write",
                contents="write",
                actions="write",
            )
        )

        GithubProvider._check(report, "ada")

        self.assertEqual(report.problems, [])
