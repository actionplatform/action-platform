"""Source providers carry the credentials they are given — never the environment's."""

from action_platform.providers.source.bitbucket import SourceBitbucket
from action_platform.providers.source.github import SourceGithub
from action_platform.providers.source.gitlab import SourceGitlab
from tests.support import TempCase


class GivenCredentialsOnlyTest(TempCase):
    def setUp(self):
        super().setUp()
        self.setenv("ACTION_PLATFORM_GITHUB_TOKEN", "env-gh")
        self.setenv("GH_TOKEN", "env-gh")
        self.setenv("ACTION_PLATFORM_GITLAB_TOKEN", "env-gl")
        self.setenv("ACTION_PLATFORM_BITBUCKET_TOKEN", "env-bb")
        self.setenv("ACTION_PLATFORM_BITBUCKET_USERNAME", "env-user")

    def test_no_token_given_means_no_token(self):
        self.assertIsNone(SourceGithub(repo="acme/x").token)
        self.assertIsNone(SourceGitlab(repo="acme/x").token)
        bitbucket = SourceBitbucket(repo="acme/x")
        self.assertIsNone(bitbucket.token)
        self.assertIsNone(bitbucket.username)

    def test_the_given_token_is_kept(self):
        self.assertEqual(SourceGithub(repo="acme/x", token="ghp").token, "ghp")
        self.assertEqual(SourceGitlab(repo="acme/x", token="glp").token, "glp")
