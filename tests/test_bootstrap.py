"""action_platform.bootstrap — the one start sequence of every entry point."""

from action_platform import bootstrap
from action_platform.core.exception import ConfigError
from action_platform.settings import settings
from tests.support import TempCase, platform_repo


class BootstrapTest(TempCase):
    def setUp(self):
        super().setUp()
        self.observed = []
        self.patch(
            bootstrap,
            "observe",
            lambda component, config, version=None: self.observed.append(
                (component, config, version)
            ),
        )

    def test_loads_the_env_file_then_observes_with_what_it_set(self):
        env_file = self.tmp_path / "custom.env"
        env_file.write_text("AP_SENTRY_DSN=https://k@o1.ingest.sentry.io/1\n")
        self.delenv("AP_SENTRY_DSN")

        returned = bootstrap.bootstrap("mcp", version="9.9.9", env_file=env_file)

        self.assertIs(returned, settings)
        ((component, config, version),) = self.observed
        self.assertEqual((component, version), ("mcp", "9.9.9"))
        self.assertEqual(config.dsn, "https://k@o1.ingest.sentry.io/1")

    def test_the_shell_wins_over_the_env_file(self):
        env_file = self.tmp_path / "custom.env"
        env_file.write_text("AP_SENTRY_ENVIRONMENT=from-file\n")
        self.setenv("AP_SENTRY_ENVIRONMENT", "from-shell")

        bootstrap.bootstrap("cli", env_file=env_file)

        self.assertEqual(self.observed[0][1].environment, "from-shell")


class ProjectTest(TempCase):
    def test_the_facade_of_a_project_on_disk(self):
        repo = platform_repo(self.tmp_path)

        tool = bootstrap.project(repo)

        self.assertEqual(tool.repo_root, repo)
        self.assertTrue(tool.config.project_name)

    def test_a_directory_without_platform_toml(self):
        with self.assertRaisesRegex(ConfigError, "platform.toml not found"):
            bootstrap.project(self.tmp_path)
