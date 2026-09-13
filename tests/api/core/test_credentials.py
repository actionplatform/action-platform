"""action_platform.api.core.credentials — per-request git credentials that never touch the process environment."""

from __future__ import annotations

import os
import subprocess
import threading
import unittest

from action_platform.core.flow import git
from tests.support import TempCase

try:
    from action_platform.api.core.credentials import SourceCredentials, git_auth
except ImportError:
    SourceCredentials = git_auth = None


@unittest.skipUnless(git_auth, "fastapi is not installed")
class GitAuthTest(TempCase):
    def test_scopes_credentials_to_the_request(self):
        self.delenv("GIT_CONFIG_COUNT")
        creds = SourceCredentials(kind="gitlab", token="glpat-x")

        with git_auth(creds):
            env = git.git_env()
            self.assertEqual(env["GIT_CONFIG_KEY_0"], "credential.helper")
            self.assertEqual(env["AP_GIT_USER"], "oauth2")
            self.assertEqual(env["AP_GIT_TOKEN"], "glpat-x")
            self.assertEqual(env["GIT_TERMINAL_PROMPT"], "0")
            self.assertNotIn("AP_GIT_TOKEN", os.environ)

        self.assertNotIn("AP_GIT_TOKEN", git.git_env())
        self.assertNotIn("credential.helper", git.git_env().values())

    def test_concurrent_requests_keep_their_own_credentials(self):
        seen: dict[str, str] = {}
        gate = threading.Barrier(2)

        def request(name: str, token: str) -> None:
            with git_auth(SourceCredentials(kind="github", token=token)):
                gate.wait()
                seen[name] = git.git_env()["AP_GIT_TOKEN"]
                gate.wait()

        threads = [
            threading.Thread(target=request, args=("a", "token-a")),
            threading.Thread(target=request, args=("b", "token-b")),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(seen, {"a": "token-a", "b": "token-b"})

    def test_git_reads_the_helper(self):
        creds = SourceCredentials(kind="github", token="ghp_test")

        with git_auth(creds):
            out = subprocess.run(
                ["git", "credential", "fill"],
                input="protocol=https\nhost=github.com\n\n",
                capture_output=True,
                text=True,
                cwd=self.tmp_path,
                check=True,
                env=git.git_env(),
            ).stdout

        self.assertIn("username=x-access-token", out)
        self.assertIn("password=ghp_test", out)
