"""HostConnector: finishing an OAuth connection and creating the GitHub App, each failure raised as HostConnectError."""

import unittest
from types import SimpleNamespace
from unittest import mock

from action_platform.core.exception import ProviderError
from app.core.shared.credentials import OAuthApp
from app.services.integrations.hosts import (
    BitbucketProvider,
    GithubProvider,
    GitlabProvider,
    HostConnectError,
    HostConnector,
)

ORG = SimpleNamespace(id="o1")


class FakeWrites:
    def __init__(self, app=None):
        self.app = app
        self.connected = []
        self.usernames = []
        self.saved = []

    def oauth_app(self, provider):
        return self.app

    def connect_oauth_host(self, *args, username=None):
        self.connected.append(args)
        self.usernames.append(username)

    def save_oauth_app(self, *args):
        self.saved.append(args)


class FinishTest(unittest.TestCase):
    def test_missing_oauth_app_raises(self):
        with self.assertRaisesRegex(HostConnectError, "GitLab OAuth app"):
            HostConnector(FakeWrites()).finish(ORG, "gitlab", "https://ap", "c", None)

    def test_provider_failure_raises(self):
        writes = FakeWrites(OAuthApp("id", "secret", None))

        with mock.patch.object(
            GitlabProvider, "exchange_code", side_effect=ProviderError("bad code")
        ):
            with self.assertRaisesRegex(HostConnectError, "bad code"):
                HostConnector(writes).finish(ORG, "gitlab", "https://ap", "c", None)

        self.assertEqual(writes.connected, [])

    def test_connected_host_is_stored(self):
        writes = FakeWrites(OAuthApp("id", "secret", None))

        with (
            mock.patch.object(
                GitlabProvider, "exchange_code", return_value=("tok", None, None)
            ),
            mock.patch.object(GitlabProvider, "identity", return_value=("ana", "Ana")),
        ):
            self.assertIsNone(
                HostConnector(writes).finish(ORG, "gitlab", "https://ap", "c", None)
            )

        self.assertEqual(writes.connected[0][:4], ("o1", "gitlab", "ana", "tok"))


class CreateGithubAppTest(unittest.TestCase):
    def test_created_app_answers_its_slug(self):
        writes = FakeWrites()

        with mock.patch.object(
            GithubProvider,
            "convert_manifest",
            return_value={"client_id": "i", "client_secret": "s", "slug": "ap"},
        ):
            self.assertEqual(HostConnector(writes).create_github_app("c"), "ap")

        self.assertEqual(writes.saved, [("github", "i", "s", None, "ap")])

    def test_refused_manifest_raises(self):
        writes = FakeWrites()

        with mock.patch.object(
            GithubProvider,
            "convert_manifest",
            side_effect=ProviderError("GitHub app creation failed"),
        ):
            with self.assertRaisesRegex(HostConnectError, "creation failed"):
                HostConnector(writes).create_github_app("c")

        self.assertEqual(writes.saved, [])


class OwnerTest(unittest.TestCase):
    def test_github_owner_is_the_installation_account(self):
        with mock.patch.object(
            GithubProvider, "installation_owner", return_value="acme"
        ) as found:
            self.assertEqual(GithubProvider().owner("tok", "42"), "acme")

        found.assert_called_once_with("tok", "42")

    def test_github_without_installation_has_no_owner(self):
        self.assertIsNone(GithubProvider().owner("tok", None))

    def test_bitbucket_owner_is_the_first_workspace(self):
        with mock.patch.object(
            BitbucketProvider, "first_workspace", return_value="team"
        ):
            self.assertEqual(BitbucketProvider().owner("tok", None), "team")

    def test_gitlab_has_no_owner(self):
        self.assertIsNone(GitlabProvider().owner("tok", "42"))

    def test_connector_stores_the_provider_owner(self):
        writes = FakeWrites(OAuthApp("id", "secret", None))

        with (
            mock.patch.object(
                BitbucketProvider, "exchange_code", return_value=("tok", None, None)
            ),
            mock.patch.object(
                BitbucketProvider, "identity", return_value=("ana", "Ana")
            ),
            mock.patch.object(BitbucketProvider, "owner", return_value="team"),
        ):
            HostConnector(writes).finish(ORG, "bitbucket", "https://ap", "c", None)

        self.assertEqual(writes.connected[0][-1], "team")


class TokenUsernameTest(unittest.TestCase):
    def test_bitbucket_stores_its_token_username(self):
        writes = FakeWrites(OAuthApp("id", "secret", None))

        with (
            mock.patch.object(
                BitbucketProvider, "exchange_code", return_value=("tok", None, None)
            ),
            mock.patch.object(
                BitbucketProvider, "identity", return_value=("ana", "Ana")
            ),
            mock.patch.object(BitbucketProvider, "owner", return_value=None),
        ):
            HostConnector(writes).finish(ORG, "bitbucket", "https://ap", "c", None)

        self.assertEqual(writes.usernames, ["x-token-auth"])

    def test_other_hosts_store_no_username(self):
        self.assertIsNone(GithubProvider.token_username)
        self.assertIsNone(GitlabProvider.token_username)
