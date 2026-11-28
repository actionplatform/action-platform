"""action_platform.providers.source — commits, comparisons and files at a ref, read from each host instead of a clone."""

from __future__ import annotations

import base64
import io
import unittest
import urllib.error
from unittest import mock

from action_platform.core.context import CommitRow
from action_platform.providers.source import rest
from action_platform.providers.source.bitbucket import SourceBitbucket
from action_platform.providers.source.github import SourceGithub
from action_platform.providers.source.gitlab import SourceGitlab

TOML = '[project]\nname = "x"\n'


def encoded(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


class GithubReadsTest(unittest.TestCase):
    def setUp(self):
        self.host = SourceGithub(repo="acme/x", token="ghp")

    def commit(self, sha, message):
        return {
            "sha": sha,
            "commit": {
                "message": message,
                "author": {"name": "Ada", "date": "2026-11-27T10:00:00Z"},
            },
        }

    def test_commits_newest_first_with_the_subject_only(self):
        with mock.patch.object(
            rest,
            "call",
            return_value=[
                self.commit("b", "feat: b\n\nbody"),
                self.commit("a", "fix: a"),
            ],
        ) as call:
            rows = self.host.commits("acme/x", "feature/7-x", 2)

        self.assertIn(
            "/repos/acme/x/commits?sha=feature%2F7-x&per_page=2", call.call_args[0][1]
        )
        self.assertEqual([r.subject for r in rows], ["feat: b", "fix: a"])
        self.assertIsInstance(rows[0], CommitRow)
        self.assertEqual((rows[0].author, rows[0].date.hour), ("Ada", 10))

    def test_compare_reverses_github_s_oldest_first(self):
        with mock.patch.object(
            rest,
            "call",
            return_value={
                "commits": [self.commit("a", "old"), self.commit("b", "new")]
            },
        ) as call:
            rows = self.host.compare("acme/x", "v1.0.0", "master")

        self.assertIn("/compare/v1.0.0...master", call.call_args[0][1])
        self.assertEqual([r.sha for r in rows], ["b", "a"])

    def test_file_decodes_and_a_missing_one_is_none(self):
        with mock.patch.object(
            rest, "call", return_value={"type": "file", "content": encoded(TOML)}
        ):
            self.assertEqual(self.host.file("acme/x", "master", "platform.toml"), TOML)

        with mock.patch.object(rest, "call", side_effect=rest.Missing("404")):
            self.assertIsNone(self.host.file("acme/x", "master", "platform.toml"))

        with mock.patch.object(rest, "call", return_value=[{"type": "file"}]):
            self.assertIsNone(self.host.file("acme/x", "master", "apps"))


class GitlabReadsTest(unittest.TestCase):
    def setUp(self):
        self.host = SourceGitlab(repo="acme/x", token="glpat")

    def commit(self, sha, title):
        return {
            "id": sha,
            "title": title,
            "author_name": "Ada",
            "authored_date": "2026-11-27T10:00:00Z",
        }

    def test_commits_compare_and_file(self):
        with mock.patch.object(
            rest, "call", return_value=[self.commit("b", "feat: b")]
        ) as call:
            rows = self.host.commits("acme/x", "master", 1)

        self.assertIn(
            "/projects/acme%2Fx/repository/commits?ref_name=master&per_page=1",
            call.call_args[0][1],
        )
        self.assertEqual(
            (rows[0].sha, rows[0].subject, rows[0].author), ("b", "feat: b", "Ada")
        )

        with mock.patch.object(
            rest,
            "call",
            return_value={
                "commits": [self.commit("a", "old"), self.commit("b", "new")]
            },
        ) as call:
            rows = self.host.compare("acme/x", "v1.0.0", "master")

        self.assertIn("/repository/compare?from=v1.0.0&to=master", call.call_args[0][1])
        self.assertEqual([r.sha for r in rows], ["b", "a"])

        with mock.patch.object(
            rest, "call", return_value={"content": encoded(TOML)}
        ) as call:
            self.assertEqual(
                self.host.file("acme/x", "master", "apps/api/platform.toml"), TOML
            )

        self.assertIn(
            "/repository/files/apps%2Fapi%2Fplatform.toml?ref=master",
            call.call_args[0][1],
        )

        with mock.patch.object(rest, "call", side_effect=rest.Missing("404")):
            self.assertIsNone(self.host.file("acme/x", "master", "platform.toml"))


class BitbucketReadsTest(unittest.TestCase):
    def setUp(self):
        self.host = SourceBitbucket(repo="acme/x", token="t")

    def commit(self, sha, message):
        return {
            "hash": sha,
            "message": message,
            "author": {"raw": "Ada <ada@x>"},
            "date": "2026-11-27T10:00:00+00:00",
        }

    def test_commits_compare_and_file(self):
        with mock.patch.object(
            rest, "call", return_value={"values": [self.commit("b", "feat: b\n")]}
        ):
            rows = self.host.commits("acme/x", "master", 1)

        self.assertEqual(
            (rows[0].sha, rows[0].subject, rows[0].author), ("b", "feat: b", "Ada")
        )

        with mock.patch.object(
            rest,
            "get_values",
            return_value=[self.commit("b", "new"), self.commit("a", "old")],
        ) as values:
            rows = self.host.compare("acme/x", "v1.0.0", "master")

        self.assertIn("/commits/master?exclude=v1.0.0", values.call_args[0][0])
        self.assertEqual([r.sha for r in rows], ["b", "a"])

        with mock.patch.object(rest, "text", return_value=TOML) as text:
            self.assertEqual(self.host.file("acme/x", "master", "platform.toml"), TOML)

        self.assertIn(
            "/repositories/acme/x/src/master/platform.toml", text.call_args[0][0]
        )


class RestMissingTest(unittest.TestCase):
    def not_found(self, *args, **kwargs):
        raise urllib.error.HTTPError(
            "https://x", 404, "Not Found", {}, io.BytesIO(b'{"message": "Not Found"}')
        )

    def test_a_404_is_missing_and_text_answers_none(self):
        with mock.patch.object(rest.destination, "urlopen", side_effect=self.not_found):
            with self.assertRaises(rest.Missing):
                rest.call("GET", "https://x", {})

            self.assertIsNone(rest.text("https://x", {}))
