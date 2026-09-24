"""action_platform.env — a .env fills in what the shell did not set."""

import os
from pathlib import Path

from action_platform.env import DotEnv, load
from tests.support import TempCase


class DotEnvTest(TempCase):
    def test_reads_quotes_exports_and_comments_and_never_overrides(self):
        path = Path(self.tmp_path) / ".env"
        path.write_text(
            "# db\nexport AP_X=\"one two\"\nAP_Y=plain\nAP_Z='q'\nbroken line\n"
        )
        self.setenv("AP_Y", "shell")

        applied = DotEnv(path).apply()

        self.assertEqual(applied, ["AP_X", "AP_Z"])
        self.assertEqual(os.environ["AP_X"], "one two")
        self.assertEqual(os.environ["AP_Y"], "shell")
        self.assertEqual(os.environ["AP_Z"], "q")

    def test_missing_file_is_nothing(self):
        self.assertEqual(DotEnv(Path(self.tmp_path) / "nope").apply(), [])

    def test_load_reads_the_path_it_is_given(self):
        path = Path(self.tmp_path) / "custom.env"
        path.write_text("AP_LOADED=yes\n")
        self.delenv("AP_LOADED")

        self.assertEqual(load(path), ["AP_LOADED"])
        self.assertEqual(os.environ["AP_LOADED"], "yes")
