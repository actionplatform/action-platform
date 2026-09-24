"""The HostProvider contract: the typed access report and the JSON the web app reads from it."""

import unittest
from unittest import mock

from app.core.abc import AccessReport, Owner
from app.core.shared.credentials import Credentials
from app.services.integrations.hosts.access import Probe
from app.services.integrations.hosts.gitlab import GitlabProvider


class AccessReportTest(unittest.TestCase):
    def test_refused_report_answers_not_ok(self):
        report = AccessReport.refused("gitlab", "GitLab", 401)

        self.assertFalse(report.ok)
        self.assertEqual(
            report.as_dict(),
            {
                "ok": False,
                "error": "token rejected by GitLab (401); reconnect the host",
            },
        )

    def test_report_keeps_the_web_shape(self):
        report = AccessReport(
            kind="bitbucket",
            login="ana",
            installations=[Owner("acme", "org", "all", "write", "write")],
        )

        self.assertTrue(report.ok)
        self.assertEqual(
            report.as_dict(),
            {
                "ok": True,
                "kind": "bitbucket",
                "login": "ana",
                "installations": [
                    {
                        "account": "acme",
                        "kind": "org",
                        "repositories": "all",
                        "administration": "write",
                        "contents": "write",
                        "actions": "none",
                        "canCreateRepos": True,
                        "selected": None,
                        "configureUrl": None,
                    }
                ],
                "installUrl": None,
                "problems": [],
            },
        )


class ProviderAccessTest(unittest.TestCase):
    creds = Credentials("gitlab", "t", None, None, None)

    def test_provider_answers_a_report(self):
        answers = {
            "https://gitlab.com/api/v4/user": (
                200,
                {"username": "ana", "can_create_project": True},
            ),
        }

        with mock.patch.object(
            Probe, "get", lambda self, url: answers.get(url, (200, []))
        ):
            report = GitlabProvider().access(self.creds, None)

        self.assertIsInstance(report, AccessReport)
        self.assertEqual(report.login, "ana")
        self.assertEqual([o.account for o in report.installations], ["ana"])

    def test_rejected_token_answers_a_refused_report(self):
        with mock.patch.object(Probe, "get", lambda self, url: (401, None)):
            report = GitlabProvider().access(self.creds, None)

        self.assertFalse(report.ok)
        self.assertIn("GitLab (401)", report.error)
