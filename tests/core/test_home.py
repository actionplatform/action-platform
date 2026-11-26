"""action_platform.core.home — the config directory and the profile folder inside it."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from action_platform.core import home
from action_platform.core.exception import ActionPlatformError
from action_platform.plugins import options, state
from action_platform.remote import credentials
from tests.support import TempCase


class HomeTest(TempCase):
    def setUp(self):
        super().setUp()
        self.setenv("AP_HOME", str(self.tmp_path))
        self.delenv("AP_PROFILE")
        self.delenv("AP_SERVER")
        self.delenv("AP_TOKEN")
        self.root = self.tmp_path / "action-platform"

    def test_without_a_profile_nothing_moves(self):
        self.assertEqual(home.home(), self.root)
        self.assertEqual(credentials.path(), self.root / "credentials.json")
        self.assertEqual(state.path(), self.root / "plugins.json")
        self.assertEqual(options.options_dir(), self.root / "plugins")

    def test_a_profile_is_a_folder_next_to_the_default_files(self):
        self.setenv("AP_PROFILE", "abc")

        self.assertEqual(credentials.path(), self.root / "abc" / "credentials.json")
        self.assertEqual(state.path(), self.root / "abc" / "plugins.json")
        self.assertEqual(options.options_dir(), self.root / "abc" / "plugins")

    def test_profiles_keep_separate_logins(self):
        credentials.save(credentials.Credentials("https://default.example", "t0"))
        self.setenv("AP_PROFILE", "abc")
        credentials.save(credentials.Credentials("https://abc.example", "t1"))
        self.setenv("AP_PROFILE", "xpto")

        self.assertIsNone(credentials.load())

        self.setenv("AP_PROFILE", "abc")
        self.assertEqual(credentials.load().server, "https://abc.example")
        self.delenv("AP_PROFILE")
        self.assertEqual(credentials.load().server, "https://default.example")

    def test_without_ap_home_it_is_under_the_user_folder(self):
        self.delenv("AP_HOME")
        self.delenv("XDG_CONFIG_HOME")
        self.setenv("AP_PROFILE", "xpto")

        self.assertEqual(home.home(), Path.home() / ".action-platform" / "xpto")

    def test_a_name_that_escapes_or_collides_is_refused(self):
        for name in ("../x", "a/b", ".hidden", "plugins", "workspaces", "a b"):
            self.setenv("AP_PROFILE", name)
            with self.assertRaises(ActionPlatformError, msg=name):
                home.home()


class ProfileOptionTest(TempCase):
    def setUp(self):
        super().setUp()
        self.setenv("AP_HOME", str(self.tmp_path))
        self.delenv("AP_PROFILE")
        self.delenv("AP_SERVER")
        self.delenv("AP_TOKEN")

    def test_the_option_selects_the_profile_for_the_command(self):
        from action_platform.cli.setup import app

        credentials.save(credentials.Credentials("https://default.example", "t0"))

        result = CliRunner().invoke(app, ["--profile", "abc", "whoami"])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("not logged in", str(result.exception or result.output).lower())

    def test_a_bad_profile_is_refused(self):
        from action_platform.cli.setup import app

        result = CliRunner().invoke(app, ["--profile", "../up", "whoami"])

        self.assertIsInstance(result.exception, ActionPlatformError)
