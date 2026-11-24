"""app.services.workspace.git_auth — per-request git credentials that never touch the process environment."""

from __future__ import annotations

import os
import subprocess
import threading
import unittest

from action_platform.core.flow import git
from action_platform.testing.fixtures import TempCase

try:
    from app.services.workspace.git_auth import SourceCredentials, git_auth
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

    def fill(self, protocol: str, host: str) -> str:
        return subprocess.run(
            ["git", "credential", "fill"],
            input=f"protocol={protocol}\nhost={host}\n\n",
            capture_output=True,
            text=True,
            cwd=self.tmp_path,
            env=git.git_env(),
        ).stdout

    def test_the_token_reaches_only_the_connections_origin(self):
        with git_auth(SourceCredentials(kind="github", token="ghp_test")):
            self.assertIn("password=ghp_test", self.fill("https", "github.com"))

            for protocol, host in (
                ("https", "evil.example.com"),
                ("https", "github.com.evil.example.com"),
                ("https", "github.com:8443"),
                ("http", "github.com"),
                ("https", "gitlab.com"),
            ):
                with self.subTest(protocol=protocol, host=host):
                    self.assertNotIn("ghp_test", self.fill(protocol, host))

    def test_self_hosted_origins_keep_their_port(self):
        creds = SourceCredentials(
            kind="gitlab", token="glpat-x", base_url="https://git.example.com:8443"
        )

        with git_auth(creds):
            self.assertIn(
                "password=glpat-x", self.fill("https", "git.example.com:8443")
            )
            self.assertNotIn("glpat-x", self.fill("https", "git.example.com"))
            self.assertNotIn("glpat-x", self.fill("https", "gitlab.com"))

        ghe = SourceCredentials(
            kind="github", token="ghp_e", base_url="https://ghe.example.com/api/v3"
        )

        with git_auth(ghe):
            self.assertIn("password=ghp_e", self.fill("https", "ghe.example.com"))
            self.assertNotIn("ghp_e", self.fill("https", "github.com"))

    def test_a_connection_without_an_origin_offers_no_token(self):
        for creds in (
            SourceCredentials(kind="other", token="t-1"),
            SourceCredentials(token="t-1"),
            SourceCredentials(
                kind="gitlab", token="t-1", base_url="https://u:p@x.example.com"
            ),
        ):
            with self.subTest(creds=creds), git_auth(creds):
                self.assertNotIn("t-1", git.git_env().values())
                self.assertNotIn("t-1", self.fill("https", "x.example.com"))

    def test_a_refused_clone_says_where_the_token_is_scoped(self):
        from app.services.workspace.checkout import clone_problem

        with git_auth(SourceCredentials(kind="github", token="ghp_test")):
            problem = clone_problem(
                "https://github.com.evil.example.com/acme/x.git",
                "fatal: could not read Username for 'https://github.com.evil.example.com'",
            )
            same = clone_problem(
                "https://github.com/acme/x.git",
                "fatal: could not read Username for 'https://github.com'",
            )

        self.assertIn("scoped to https://github.com", problem)
        self.assertIn("https://github.com.evil.example.com", problem)
        self.assertNotIn("scoped", same)


@unittest.skipUnless(git_auth, "fastapi is not installed")
class ConnectionOriginTest(unittest.TestCase):
    def test_public_instances_and_self_hosted_base_urls(self):
        from app.core.shared.credentials import connection_origin

        cases = {
            ("github", None): "https://github.com",
            ("github", "https://api.github.com"): "https://github.com",
            ("github", "https://ghe.example.com/api/v3"): "https://ghe.example.com",
            ("gitlab", None): "https://gitlab.com",
            ("gitlab", "https://git.example.com:8443/"): "https://git.example.com:8443",
            ("bitbucket", None): "https://bitbucket.org",
            ("other", "https://git.example.com/acme/x.git"): "https://git.example.com",
        }

        for (kind, base_url), expected in cases.items():
            with self.subTest(kind=kind, base_url=base_url):
                self.assertEqual(connection_origin(kind, base_url).url, expected)

        self.assertIsNone(connection_origin("other", None))
        self.assertIsNone(connection_origin(None, None))
        self.assertIsNone(connection_origin("gitlab", "ssh://git.example.com"))
