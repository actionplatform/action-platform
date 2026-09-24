"""action_platform.core.facade — the facade takes its Config from the caller."""

from action_platform import ActionPlatform, Config
from action_platform.core.exception import ConfigError
from tests.support import TempCase


class FacadeConfigTest(TempCase):
    def test_a_config_is_required(self):
        with self.assertRaises(TypeError):
            ActionPlatform()

    def test_none_fails_at_construction(self):
        with self.assertRaisesRegex(ConfigError, "needs a Config"):
            ActionPlatform(config=None, repo_root=self.tmp_path)

    def test_the_given_config_is_used_as_is(self):
        config = Config(project_name="orders")

        tool = ActionPlatform(config, repo_root=self.tmp_path)

        self.assertIs(tool.config, config)
        self.assertEqual(tool.repo_root, self.tmp_path)
