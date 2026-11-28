"""action_platform.providers.source — releases and pull requests in the platform's shape, from each host's answer."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest import mock

from action_platform.abc.source_host import ListsPullRequests, PublishesReleases
from action_platform.core.context import PullRequestRow, ReleaseRow
from action_platform.providers.source import rest
from action_platform.providers.source.bitbucket import SourceBitbucket
from action_platform.providers.source.generic import SourceGeneric
from action_platform.providers.source.github import SourceGithub
from action_platform.providers.source.gitlab import SourceGitlab


class GithubActivityTest(unittest.TestCase):
    def test_releases_and_pull_requests(self):
        host = SourceGithub(repo="acme/x", token="ghp")
        release = {
            "tag_name": "v1.2.0",
            "name": "Release 1.2.0",
            "body": "notes",
            "html_url": "https://gh/r/1",
            "author": {"login": "ada"},
            "prerelease": False,
            "draft": False,
            "published_at": "2026-09-17T10:00:00Z",
        }
        pull = {
            "number": 7,
            "title": "Add x",
            "html_url": "https://gh/p/7",
            "user": {"login": "ada"},
            "head": {"ref": "feature/7"},
            "base": {"ref": "develop"},
            "state": "closed",
            "merged_at": "2026-09-17T11:00:00Z",
            "draft": False,
            "created_at": "2026-09-17T09:00:00Z",
            "updated_at": "2026-09-17T11:00:00Z",
        }

        with mock.patch(
            "action_platform.providers.source.github.rest.get_pages",
            side_effect=[[release], [pull]],
        ) as pages:
            releases = host.releases("acme/x")
            pulls = host.pull_requests("acme/x")

        self.assertEqual(
            (releases[0].tag, releases[0].author, releases[0].source),
            ("v1.2.0", "ada", "github"),
        )
        self.assertIsInstance(releases[0], ReleaseRow)
        self.assertIsInstance(pulls[0], PullRequestRow)
        self.assertEqual(releases[0].published_at.hour, 10)
        self.assertEqual(
            (pulls[0].number, pulls[0].state, pulls[0].head, pulls[0].base),
            (7, "merged", "feature/7", "develop"),
        )
        self.assertEqual(
            pages.call_args_list[0].args[0],
            "https://api.github.com/repos/acme/x/releases",
        )
        self.assertEqual(pages.call_args_list[0].args[1]["authorization"], "Bearer ghp")


class GitlabActivityTest(unittest.TestCase):
    def test_merge_requests_and_rc_releases(self):
        host = SourceGitlab(
            repo="acme/x", token="glpat", base_url="https://git.acme.io"
        )
        release = {
            "tag_name": "v2.0.0-rc.1",
            "name": "rc",
            "description": "",
            "author": {"username": "ada"},
            "commit": {"id": "abcdef1234"},
            "created_at": "2026-09-17T10:00:00Z",
        }
        mr = {
            "iid": 3,
            "title": "MR",
            "web_url": "https://git.acme.io/acme/x/-/merge_requests/3",
            "author": {"username": "ada"},
            "source_branch": "feature/3",
            "target_branch": "main",
            "state": "opened",
            "draft": True,
            "created_at": "2026-09-17T09:00:00Z",
            "updated_at": "2026-09-17T09:30:00Z",
        }

        with mock.patch(
            "action_platform.providers.source.gitlab.rest.get_pages",
            side_effect=[[release], [mr]],
        ) as pages:
            releases = host.releases("acme/x")
            pulls = host.pull_requests("acme/x")

        self.assertTrue(releases[0].prerelease)
        self.assertEqual(releases[0].sha, "abcdef1")
        self.assertEqual(
            releases[0].url, "https://git.acme.io/acme/x/-/releases/v2.0.0-rc.1"
        )
        self.assertEqual((pulls[0].state, pulls[0].draft), ("open", True))
        self.assertIn(
            "/api/v4/projects/acme%2Fx/releases", pages.call_args_list[0].args[0]
        )


class BitbucketActivityTest(unittest.TestCase):
    def test_tags_are_releases_and_declined_is_closed(self):
        host = SourceBitbucket(repo="acme/x", token="app-pass", username="ada")
        tag = {
            "name": "v0.1.0",
            "message": "first",
            "links": {"html": {"href": "https://bb/t"}},
            "target": {
                "hash": "1234567abc",
                "date": "2026-09-17T10:00:00+00:00",
                "author": {"user": {"display_name": "Ada"}},
            },
        }
        pr = {
            "id": 9,
            "title": "PR",
            "links": {"html": {"href": "https://bb/p/9"}},
            "author": {"display_name": "Ada"},
            "source": {"branch": {"name": "feature/9"}},
            "destination": {"branch": {"name": "develop"}},
            "state": "DECLINED",
            "created_on": "2026-09-17T09:00:00+00:00",
            "updated_on": "2026-09-17T10:00:00+00:00",
        }

        with mock.patch(
            "action_platform.providers.source.bitbucket.rest.get_values",
            side_effect=[[tag], [pr]],
        ):
            releases = host.releases("acme/x")
            pulls = host.pull_requests("acme/x")

        self.assertEqual(
            (releases[0].tag, releases[0].sha, releases[0].author),
            ("v0.1.0", "1234567", "Ada"),
        )
        self.assertEqual((pulls[0].state, pulls[0].merged_at), ("closed", None))


class GenericTest(unittest.TestCase):
    def test_a_plain_git_server_has_no_releases_to_read(self):
        host = SourceGeneric(repo="x")

        self.assertNotIsInstance(host, PublishesReleases)
        self.assertNotIsInstance(host, ListsPullRequests)
        self.assertFalse(hasattr(host, "releases"))


class IncrementalPullRequestsTest(unittest.TestCase):
    def page(self, start, stamp):
        return [
            {
                "number": n,
                "title": "t",
                "html_url": "u",
                "user": {"login": "ada"},
                "head": {"ref": "feature/1"},
                "base": {"ref": "develop"},
                "state": "open",
                "draft": False,
                "created_at": stamp,
                "updated_at": stamp,
            }
            for n in range(start, start + 100)
        ]

    def test_paging_stops_at_the_first_page_older_than_the_last_sync(self):
        pages = [
            self.page(0, "2026-11-28T10:00:00Z"),
            self.page(100, "2026-11-01T10:00:00Z"),
            self.page(200, "2026-10-01T10:00:00Z"),
        ]

        with mock.patch.object(rest, "call", side_effect=pages) as call:
            rows = SourceGithub(repo="acme/x", token="ghp").pull_requests(
                "acme/x", since=datetime(2026, 11, 20)
            )

        self.assertEqual(call.call_count, 2)
        self.assertEqual(len(rows), 200)

        with mock.patch.object(rest, "call", side_effect=pages + [[]]) as call:
            SourceGithub(repo="acme/x", token="ghp").pull_requests("acme/x")

        self.assertEqual(call.call_count, 4)

    def test_bitbucket_stops_following_next(self):
        old = {
            "id": 1,
            "title": "t",
            "links": {"html": {"href": "u"}},
            "author": {"display_name": "ada"},
            "source": {"branch": {"name": "feature/1"}},
            "destination": {"branch": {"name": "develop"}},
            "state": "OPEN",
            "created_on": "2026-10-01T10:00:00+00:00",
            "updated_on": "2026-10-01T10:00:00+00:00",
        }

        with mock.patch.object(
            rest,
            "call",
            return_value={
                "values": [old],
                "next": "https://api.bitbucket.org/2.0/x?page=2",
            },
        ) as call:
            SourceBitbucket(repo="acme/x", token="t").pull_requests(
                "acme/x", since=datetime(2026, 11, 20)
            )

        self.assertEqual(call.call_count, 1)
