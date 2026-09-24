"""action_platform.options — one configuration slice per concern, parsed from a mapping."""

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from action_platform.options import (
    ApiConfig,
    DatabaseConfig,
    GitConfig,
    ObservabilityConfig,
    SourceTokens,
    TemplatesConfig,
    WorkspacesConfig,
)


class SlicesFromEnvTest(unittest.TestCase):
    def test_an_empty_environment_gives_the_defaults(self):
        for slice_ in (
            ApiConfig,
            DatabaseConfig,
            GitConfig,
            ObservabilityConfig,
            SourceTokens,
            TemplatesConfig,
            WorkspacesConfig,
        ):
            with self.subTest(slice_.__name__):
                self.assertEqual(slice_.from_env({}), slice_())

    def test_templates_index_follows_the_ref(self):
        config = TemplatesConfig.from_env(
            {
                "ACTION_PLATFORM_TEMPLATES_REF": "v2",
                "ACTION_PLATFORM_TEMPLATES": "/srv/templates",
            }
        )

        self.assertEqual(config.ref, "v2")
        self.assertEqual(config.dir, "/srv/templates")
        self.assertEqual(
            config.index_url,
            "https://raw.githubusercontent.com/actionplatform/templates/v2/index.json",
        )

    def test_git_policy_and_identity(self):
        config = GitConfig.from_env(
            {
                "AP_ALLOW_FILE_URLS": "1",
                "ACTION_PLATFORM_GIT_HOSTS": " GitHub.com, ,gitlab.acme.com",
                "AP_GIT_AUTHOR_NAME": "Bot",
            }
        )

        self.assertTrue(config.allow_file_urls)
        self.assertFalse(config.allow_insecure_http)
        self.assertEqual(config.hosts, ("github.com", "gitlab.acme.com"))
        self.assertEqual(config.author_name, "Bot")
        self.assertEqual(config.author_email, "cloud@actionplatform.io")

    def test_tokens_fall_back_to_the_host_cli_names(self):
        tokens = SourceTokens.from_env({"GH_TOKEN": "gh", "GITLAB_TOKEN": "gl"})

        self.assertEqual((tokens.github, tokens.gitlab), ("gh", "gl"))

    def test_api_database_workspaces_and_observability(self):
        env = {
            "AP_API_TOKEN": "t",
            "AP_ALLOW_UNAUTHENTICATED": "1",
            "BETTER_AUTH_SECRET": "s",
            "PUBLIC_URL": "https://ap.example.com",
            "AP_DATABASE_URL": "sqlite://",
            "AP_DATABASE_AUTO_MIGRATE": "false",
            "AP_WORKSPACES": "/srv/ws",
            "AP_WORKSPACE_TTL": "0",
            "AP_SENTRY_DSN": "https://k@o1.ingest.sentry.io/1",
            "AP_SENTRY_TRACES_SAMPLE_RATE": "0.5",
        }

        api = ApiConfig.from_env(env)
        database = DatabaseConfig.from_env(env)
        workspaces = WorkspacesConfig.from_env(env)
        observability = ObservabilityConfig.from_env(env)

        self.assertEqual(
            (api.token, api.allow_unauthenticated, api.auth_secret, api.public_url),
            ("t", True, "s", "https://ap.example.com"),
        )
        self.assertEqual((database.url, database.auto_migrate), ("sqlite://", False))
        self.assertEqual((workspaces.root, workspaces.ttl), (Path("/srv/ws"), 0))
        self.assertEqual(
            (observability.dsn, observability.traces_sample_rate),
            ("https://k@o1.ingest.sentry.io/1", 0.5),
        )

    def test_tokens_by_source_host_kind(self):
        tokens = SourceTokens(github="gh", bitbucket="bb", bitbucket_username="ada")

        self.assertEqual(tokens.token("github"), "gh")
        self.assertIsNone(tokens.token("generic"))
        self.assertEqual(tokens.username("bitbucket"), "ada")
        self.assertIsNone(tokens.username("github"))

    def test_a_slice_is_frozen(self):
        with self.assertRaises(FrozenInstanceError):
            GitConfig().allow_file_urls = True
