"""action_platform.providers.source.bitbucket — how credentials reach the REST API."""

from __future__ import annotations

import base64
import unittest

from action_platform.providers.source.bitbucket import SourceBitbucket


class HeadersTest(unittest.TestCase):
    def test_app_password_goes_as_basic(self):
        host = SourceBitbucket(repo="acme/x", token="app-pass", username="ada")
        raw = base64.b64encode(b"ada:app-pass").decode()

        self.assertEqual(host._headers(), {"authorization": f"Basic {raw}"})

    def test_oauth_token_goes_as_bearer_even_with_the_git_pseudo_user(self):
        host = SourceBitbucket(
            repo="acme/x", token="oauth-token", username="x-token-auth"
        )

        self.assertEqual(host._headers(), {"authorization": "Bearer oauth-token"})

    def test_token_without_username_goes_as_bearer(self):
        host = SourceBitbucket(repo="acme/x", token="tok", username=None)

        self.assertEqual(host._headers(), {"authorization": "Bearer tok"})
