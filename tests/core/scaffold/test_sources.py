"""action_platform.core.scaffold.sources — where the official templates come from is the store's config."""

from action_platform.core.exception import TemplateError
from action_platform.core.scaffold.sources import LocalTemplateStore
from action_platform.options import TemplatesConfig
from tests.support import TempCase


class OfficialTemplatesTest(TempCase):
    def test_a_local_directory_from_the_given_config(self):
        self.setenv("ACTION_PLATFORM_TEMPLATES", str(self.tmp_path / "from-env"))

        store = LocalTemplateStore(TemplatesConfig(dir=str(self.tmp_path)))

        self.assertEqual(store.official(), self.tmp_path)

    def test_the_environment_when_no_config_is_given(self):
        self.setenv("ACTION_PLATFORM_TEMPLATES", str(self.tmp_path))

        self.assertEqual(LocalTemplateStore().official(), self.tmp_path)

    def test_a_missing_directory_is_an_error(self):
        store = LocalTemplateStore(TemplatesConfig(dir=str(self.tmp_path / "gone")))

        with self.assertRaisesRegex(TemplateError, "missing path"):
            store.official()
