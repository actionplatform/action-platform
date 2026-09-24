"""action_platform.core.flow.git — url policy and ref validation before anything reaches git."""

from __future__ import annotations

from action_platform.core.flow import git
from tests.support import TempCase


class RemoteUrlPolicyTest(TempCase):
    def setUp(self):
        super().setUp()
        self.setenv("AP_ALLOW_FILE_URLS", "0")
        self.setenv("AP_ALLOW_INSECURE_HTTP", "0")
        self.delenv("ACTION_PLATFORM_GIT_HOSTS")

    def test_https_only_by_default(self):
        self.assertEqual(
            git.check_remote_url("https://github.com/a/b.git"),
            "https://github.com/a/b.git",
        )

        for bad in [
            "http://x/y.git",
            "file:///tmp/x",
            "ssh://git@github.com/a/b.git",
            "git@github.com:a/b.git",
            "/tmp/x",
            "-oProxyCommand=x",
        ]:
            with self.assertRaisesRegex(git.UnsafeUrl, "https:// only"):
                git.check_remote_url(bad)

    def test_operator_opt_ins(self):
        self.setenv("AP_ALLOW_INSECURE_HTTP", "1")
        self.setenv("AP_ALLOW_FILE_URLS", "1")

        git.check_remote_url("http://gitlab.internal/a/b.git")
        git.check_remote_url("file:///tmp/x")

    def test_host_allowlist_includes_subdomains(self):
        self.setenv("ACTION_PLATFORM_GIT_HOSTS", "github.com,gitlab.acme.com")

        git.check_remote_url("https://github.com/a/b.git")
        git.check_remote_url("https://code.gitlab.acme.com/a/b.git")

        with self.assertRaisesRegex(git.UnsafeUrl, "not allowed"):
            git.check_remote_url("https://bitbucket.org/a/b.git")


class RefValidationTest(TempCase):
    def test_accepts_branches_and_tags(self):
        for ok in ["main", "feature/42-login", "v1.2.3", "release/1.4.0", "web/v0.2.0"]:
            self.assertEqual(git.check_ref(ok), ok)

    def test_rejects_options_and_path_tricks(self):
        for bad in [
            "",
            "-x",
            "--upload-pack=touch /tmp/pwned",
            "a..b",
            "feature/@{1}",
            "x.lock",
            "dir/",
            "a//b",
            " main",
        ]:
            with self.assertRaises(git.BadRef):
                git.check_ref(bad)


class GitEnvTest(TempCase):
    def test_policy_keeps_git_on_https(self):
        env = git.git_env()
        keys = {
            env[f"GIT_CONFIG_KEY_{i}"]: env[f"GIT_CONFIG_VALUE_{i}"]
            for i in range(int(env["GIT_CONFIG_COUNT"]))
        }

        self.assertEqual(env["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(keys["protocol.allow"], "never")
        self.assertEqual(keys["protocol.https.allow"], "always")
